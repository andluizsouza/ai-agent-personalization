"""
Tool 1: SQL Runner - Text-to-SQL for Client Knowledge

This tool retrieves client information from the customers.db SQLite database (table: customers).
It uses Gemini 2.5 Flash to generate SQL queries based on natural language input,
with fallback logic for different search methods (client_id, postal_code, client_name).
"""

import json
import logging
import os
# Import prompt loader utility
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.prompt_loader import load_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load database schema from external file
CUSTOMERS_SCHEMA = load_prompt("customers_schema.txt")

# Load SQL generation prompt from external file
SQL_GENERATION_PROMPT = load_prompt("sql_generation.txt")


class SQLRunner:
    """
    SQL Runner Tool for retrieving client profile information.
    Implements Text-to-SQL with fallback logic.
    """

    def __init__(
        self, database_path: str = "data/customers.db", api_key: Optional[str] = None
    ):
        """
        Initialize SQL Runner.

        Args:
            database_path: Path to SQLite database file
            api_key: Google API Key (if not provided, reads from GOOGLE_API_KEY env var)
        """
        self.database_path = database_path
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        # Initialize database connection
        db_uri = f"sqlite:///{database_path}"
        self.db = SQLDatabase.from_uri(db_uri)

        # Initialize Gemini model
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0, google_api_key=self.api_key
        )

        # Create SQL query chain
        self.prompt = PromptTemplate(
            template=SQL_GENERATION_PROMPT, input_variables=["schema", "question"]
        )

        logger.info(f"SQL Runner initialized with database: {database_path}")

    def _generate_sql_query(
        self,
        search_input: str,
        search_method: str,
        postal_code: str = None,
        client_name: str = None,
    ) -> str:
        """
        Generate SQL query using Gemini based on search method.

        Args:
            search_input: The value to search for (used for client_id)
            search_method: One of 'client_id', 'postal_code_and_name'
            postal_code: Postal code (used when search_method is 'postal_code_and_name')
            client_name: Client name (used when search_method is 'postal_code_and_name')

        Returns:
            Generated SQL query string
        """
        if search_method == "client_id":
            question = f"Find the client profile where client_id is '{search_input}'"
        elif search_method == "postal_code_and_name":
            question = f"Find the client profile where postal_code is '{postal_code}' AND client_name contains '{client_name}' (case-insensitive)"
        else:
            raise ValueError(f"Invalid search method: {search_method}")

        # Generate SQL using LLM
        prompt_value = self.prompt.format(schema=CUSTOMERS_SCHEMA, question=question)
        response = self.llm.invoke(prompt_value)
        sql_query = response.content.strip()

        # Clean up the query (remove markdown code blocks if present)
        if sql_query.startswith("```sql"):
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        elif sql_query.startswith("```"):
            sql_query = sql_query.replace("```", "").strip()

        return sql_query

    def _execute_query(self, sql_query: str) -> Optional[Dict[str, Any]]:
        """
        Execute SQL query and return result.

        Args:
            sql_query: SQL query to execute

        Returns:
            Dictionary with query result or None if no results
        """
        try:
            result = self.db.run(sql_query)

            # Parse the result (SQLDatabase.run returns string representation)
            if not result or result == "[]":
                return None

            # The result is typically a string like: "[('C001', 'Bar do João', ...)]"
            # We need to parse it properly
            # For now, let's execute directly with sqlite3 for better control
            import sqlite3

            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(sql_query)
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Convert to dictionary
            result_dict = dict(row)

            # Parse JSON columns
            if result_dict.get("top3_brewery_types"):
                result_dict["top3_brewery_types"] = json.loads(
                    result_dict["top3_brewery_types"]
                )
            if result_dict.get("top5_beers_recently"):
                result_dict["top5_beers_recently"] = json.loads(
                    result_dict["top5_beers_recently"]
                )
            if result_dict.get("top3_breweries_recently"):
                result_dict["top3_breweries_recently"] = json.loads(
                    result_dict["top3_breweries_recently"]
                )

            # Create combined location field for backward compatibility
            if result_dict.get("client_city") and result_dict.get("client_state"):
                result_dict["client_location_city_state"] = (
                    f"{result_dict['client_city']}, {result_dict['client_state']}"
                )

            return result_dict

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return None

    def get_client_profile(
        self,
        client_id: Optional[str] = None,
        postal_code: Optional[str] = None,
        client_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve client profile with fallback logic.

        Tries search methods in order:
        1. client_id (if provided) - primary unique identifier
        2. postal_code AND client_name (if both provided and client_id failed) - combined fallback

        Args:
            client_id: Client ID to search for (primary identifier)
            postal_code: Postal code to search for (used with client_name for fallback)
            client_name: Client name to search for (used with postal_code for fallback)

        Returns:
            Dictionary with:
            - sql_query: The SQL query that was executed
            - search_method: The method used ('client_id', 'postal_code_and_name', 'not_found')
            - result: The client profile data or None
            - execution_time_ms: Time taken to execute
            - timestamp: ISO timestamp of execution
        """
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        result = None
        sql_query = None
        search_method = "not_found"

        # Try client_id first (primary identifier)
        if client_id:
            try:
                logger.info(f"Attempting search by client_id: {client_id}")
                sql_query = self._generate_sql_query(client_id, "client_id")
                logger.info(f"Generated SQL: {sql_query}")
                result = self._execute_query(sql_query)
                if result:
                    search_method = "client_id"
                    logger.info(f"✓ Found client by client_id: {result['client_name']}")
            except Exception as e:
                logger.error(f"Error searching by client_id: {e}")

        # Fallback to postal_code AND client_name (combined search)
        if not result and postal_code and client_name:
            try:
                logger.info(
                    f"Attempting fallback search by postal_code AND client_name: {postal_code} + {client_name}"
                )
                sql_query = self._generate_sql_query(
                    search_input=None,
                    search_method="postal_code_and_name",
                    postal_code=postal_code,
                    client_name=client_name,
                )
                logger.info(f"Generated SQL: {sql_query}")
                result = self._execute_query(sql_query)
                if result:
                    search_method = "postal_code_and_name"
                    logger.info(
                        f"✓ Found client by postal_code AND client_name: {result['client_name']}"
                    )
            except Exception as e:
                logger.error(f"Error searching by postal_code AND client_name: {e}")

        execution_time_ms = (time.time() - start_time) * 1000

        response = {
            "sql_query": sql_query,
            "search_method": search_method,
            "result": result,
            "execution_time_ms": round(execution_time_ms, 2),
            "timestamp": timestamp,
        }

        if not result:
            logger.warning("⚠ Client not found with provided search criteria")

        return response


# Convenience function for LangChain tool integration
def get_client_profile(
    client_id: Optional[str] = None,
    postal_code: Optional[str] = None,
    client_name: Optional[str] = None,
    database_path: str = "data/customers.db",
) -> Dict[str, Any]:
    """
    Retrieve client profile information from the database.

    This is the main function that will be exposed as a LangChain tool.

    Search Logic:
    1. If client_id is provided, search by client_id (primary identifier)
    2. If client_id fails or not provided, AND both postal_code and client_name are provided,
       search using postal_code AND client_name together (combined fallback)
    3. If neither method finds a match, return 'not_found'

    Args:
        client_id: Client ID to search for (e.g., 'CLT-ABC123') - primary identifier
        postal_code: Postal code to search for (e.g., '92101') - used with client_name
        client_name: Client name to search for (e.g., 'Stone') - used with postal_code
        database_path: Path to SQLite database (default: 'customers.db')

    Returns:
        Dictionary with client profile data and metadata

    Examples:
        # Search by client_id (primary)
        get_client_profile(client_id="CLT-ABC123")

        # Search by postal_code AND client_name (fallback)
        get_client_profile(postal_code="92101", client_name="Stone")

        # Try client_id first, fallback to postal_code + name
        get_client_profile(client_id="CLT-XYZ", postal_code="92101", client_name="Stone")
    """
    runner = SQLRunner(database_path=database_path)
    return runner.get_client_profile(
        client_id=client_id, postal_code=postal_code, client_name=client_name
    )


if __name__ == "__main__":
    # Test the SQL Runner
    print("=" * 80)
    print("Testing SQL Runner Tool")
    print("=" * 80)

    # Test 1: Search by client_id
    print("\n[Test 1] Search by client_id='C001':")
    result = get_client_profile(client_id="C001")
    print(json.dumps(result, indent=2))

    # Test 2: Search by postal_code
    print("\n[Test 2] Search by postal_code='92101':")
    result = get_client_profile(postal_code="92101")
    print(json.dumps(result, indent=2))

    # Test 3: Search by client_name
    print("\n[Test 3] Search by client_name='Bar':")
    result = get_client_profile(client_name="Bar")
    print(json.dumps(result, indent=2))

    # Test 4: Search with fallback (invalid client_id, valid postal_code)
    print("\n[Test 4] Fallback test (invalid client_id, valid postal_code):")
    result = get_client_profile(client_id="INVALID", postal_code="92101")
    print(json.dumps(result, indent=2))

    # Test 5: Not found
    print("\n[Test 5] Not found test:")
    result = get_client_profile(client_id="INVALID")
    print(json.dumps(result, indent=2))
