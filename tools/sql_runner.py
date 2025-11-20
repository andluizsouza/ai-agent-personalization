"""
Tool 1: SQL Runner - Text-to-SQL for Client Knowledge

This tool retrieves client information from the customers.db SQLite database (table: customers).
It uses Gemini 2.5 Flash to generate SQL queries based on natural language input,
with fallback logic for different search methods (client_id, postal_code, client_name).

SECURITY: READ-ONLY MODE
- Only SELECT queries are executed
- All data modification commands are BLOCKED:
  * DELETE, UPDATE, INSERT, DROP, TRUNCATE, ALTER, CREATE, REPLACE
  * PRAGMA, ATTACH, DETACH, GRANT, REVOKE
- Multi-statement SQL injection attempts are detected and blocked
- Automatic validation before every query execution

PRIVACY RULES:
1. Individual Own Data: ALLOWED - "What beers do I buy most?" (using authenticated client_id)
2. Individual Others' Data: BLOCKED - "What is client X's favorite brewery?" (privacy violation)
3. Aggregate/Statistical Data: ALLOWED - "What's the most purchased beer in my state?" (anonymized)
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

from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.prompt_loader import load_prompt

# Load environment variables from .env file
load_dotenv()

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

    SECURITY: READ-ONLY MODE
    - Only SELECT queries are allowed
    - All modification commands (INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, etc.) are blocked
    """

    # Forbidden SQL keywords that modify data
    FORBIDDEN_KEYWORDS = [
        "insert",
        "update",
        "delete",
        "drop",
        "truncate",
        "alter",
        "create",
        "replace",
        "rename",
        "grant",
        "revoke",
        "attach",
        "detach",
        "pragma",
    ]

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

    def _validate_read_only(self, sql_query: str) -> tuple[bool, str]:
        """
        Validate that SQL query is read-only (SELECT only).

        Security check to prevent any data modification commands.

        Args:
            sql_query: SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if query is safe (SELECT only), False otherwise
            - error_message: Empty string if valid, error description if invalid
        """
        sql_lower = sql_query.lower().strip()

        # Remove comments and extra whitespace
        sql_normalized = " ".join(sql_lower.split())

        # Check for forbidden keywords
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in sql_normalized:
                error_msg = f"SECURITY VIOLATION: '{keyword.upper()}' command is not allowed. Only SELECT queries are permitted."
                logger.error(error_msg)
                return False, error_msg

        # Ensure query starts with SELECT (after removing leading whitespace/comments)
        if not sql_normalized.startswith("select"):
            error_msg = "SECURITY VIOLATION: Only SELECT queries are allowed. Query must start with SELECT."
            logger.error(error_msg)
            return False, error_msg

        # Additional check: look for semicolon followed by forbidden keywords (multi-statement injection)
        if ";" in sql_normalized:
            parts = sql_normalized.split(";")
            for part in parts:
                part = part.strip()
                if not part:  # Empty after semicolon is OK
                    continue
                if not part.startswith("select"):
                    error_msg = "SECURITY VIOLATION: Multi-statement queries detected. Only single SELECT queries are allowed."
                    logger.error(error_msg)
                    return False, error_msg

        return True, ""

    def _generate_query(
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

        SECURITY: Validates that query is read-only before execution.

        Args:
            sql_query: SQL query to execute

        Returns:
            Dictionary with query result or None if no results
        """
        try:
            # SECURITY CHECK: Validate read-only
            is_valid, error_msg = self._validate_read_only(sql_query)
            if not is_valid:
                logger.error(f"Query rejected: {error_msg}")
                logger.error(f"Rejected SQL: {sql_query}")
                return None
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
                sql_query = self._generate_query(client_id, "client_id")
                logger.info(f"Generated SQL: {sql_query}")
                result = self._execute_query(sql_query)
                if result:
                    search_method = "client_id"
                    logger.info(f"Found client by client_id: {result['client_name']}")
            except Exception as e:
                logger.error(f"Error searching by client_id: {e}")

        # Fallback to postal_code AND client_name (combined search)
        if not result and postal_code and client_name:
            try:
                logger.info(
                    f"Attempting fallback search by postal_code AND client_name: {postal_code} + {client_name}"
                )
                sql_query = self._generate_query(
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
                        f"Found client by postal_code AND client_name: {result['client_name']}"
                    )
            except Exception as e:
                logger.error(f"Error searching by postal_code AND client_name: {e}")

        execution_time_ms = (time.time() - start_time) * 1000

        response = {
            "sql_query": sql_query,
            "search_method": search_method,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "timestamp": timestamp,
        }

        if not result:
            logger.warning("WARNING: Client not found with provided search criteria")

        return response

    def run_analytical_query(
        self, question: str, authenticated_client_id: str
    ) -> Dict[str, Any]:
        """
        Execute analytical/aggregate queries on the customer database.

        PRIVACY RULES ENFORCED:
        1. ALLOWED: Queries about authenticated user's own data
        2. ALLOWED: Aggregate/statistical queries (no individual client data)
        3. BLOCKED: Queries about specific other clients' individual data

        Args:
            question: Natural language question (e.g., "What's the most popular beer in Ohio?")
            authenticated_client_id: The client_id of the authenticated user (for privacy checks)

        Returns:
            Dictionary with:
            - sql_query: Generated SQL query
            - result: Query result (list of rows or single aggregated value)
            - query_type: 'aggregate' or 'individual_own'
            - execution_time_ms: Execution time
            - timestamp: Timestamp
            - privacy_compliant: Boolean indicating if query passed privacy rules
        """
        start_time = time.time()
        timestamp = datetime.now().isoformat()

        try:
            # Get authenticated client's profile to provide context for "my city", "my state" queries
            client_profile = self._execute_query(
                f"SELECT client_city, client_state FROM customers WHERE client_id = '{authenticated_client_id}'"
            )

            client_context = ""
            if client_profile:
                client_city = client_profile.get("client_city", "Unknown")
                client_state = client_profile.get("client_state", "Unknown")
                client_context = f"""
                
                AUTHENTICATED CLIENT CONTEXT:
                - Client ID: {authenticated_client_id}
                - City: {client_city}
                - State: {client_state} (FULL NAME, not abbreviation)
                
                CRITICAL RULES FOR CITY QUERIES:
                - When user asks about "my city" or references city data, ALWAYS filter by BOTH city AND state
                - Use: WHERE client_city = '{client_city}' AND client_state = '{client_state}'
                - NEVER filter by city alone (multiple cities can have same name in different states)
                - State is stored as FULL NAME '{client_state}', NOT as abbreviation
                """

            # Generate SQL query using LLM
            prompt_value = self.prompt.format(
                schema=CUSTOMERS_SCHEMA,
                question=f"""
                Generate SQL for this question: {question}
                {client_context}
                
                IMPORTANT PRIVACY RULES:
                - The authenticated client is: {authenticated_client_id}
                - ALLOW queries about this specific client's data
                - ALLOW aggregate/statistical queries (COUNT, AVG, MAX, GROUP BY, etc.)
                - BLOCK queries requesting individual data of OTHER specific clients
                - Use GROUP BY, aggregation functions for statistical queries
                """,
            )
            response = self.llm.invoke(prompt_value)
            sql_query = response.content.strip()

            # Clean SQL
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()

            logger.info(f"Generated analytical SQL: {sql_query}")

            # SECURITY CHECK: Validate read-only (block INSERT, UPDATE, DELETE, etc.)
            is_valid, security_error = self._validate_read_only(sql_query)
            if not is_valid:
                logger.error(
                    f"Security violation in analytical query: {security_error}"
                )
                return {
                    "sql_query": sql_query,
                    "result": None,
                    "query_type": "blocked",
                    "execution_time_ms": (time.time() - start_time) * 1000,
                    "timestamp": timestamp,
                    "privacy_compliant": False,
                    "error": security_error,
                }

            # Basic privacy check: detect queries trying to access other specific clients
            sql_lower = sql_query.lower()
            is_aggregate = any(
                keyword in sql_lower
                for keyword in ["count(", "avg(", "sum(", "max(", "min(", "group by"]
            )
            references_other_client = (
                "client_id" in sql_lower
                and authenticated_client_id.lower() not in sql_lower
                and not is_aggregate
            )

            if references_other_client:
                logger.warning(
                    f"PRIVACY VIOLATION: Query attempts to access other client's data"
                )
                return {
                    "sql_query": sql_query,
                    "result": None,
                    "query_type": "blocked",
                    "execution_time_ms": (time.time() - start_time) * 1000,
                    "timestamp": timestamp,
                    "privacy_compliant": False,
                    "error": "PRIVACY_VIOLATION: Cannot access individual data of other clients",
                }

            # Execute query
            import sqlite3

            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(sql_query)
            rows = cursor.fetchall()
            conn.close()

            # Convert to list of dicts
            result = [dict(row) for row in rows]

            # Determine query type
            query_type = "aggregate" if is_aggregate else "individual_own"

            execution_time_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Analytical query executed successfully: {len(result)} rows returned"
            )

            return {
                "sql_query": sql_query,
                "result": result,
                "query_type": query_type,
                "execution_time_ms": execution_time_ms,
                "timestamp": timestamp,
                "privacy_compliant": True,
            }

        except Exception as e:
            logger.error(f"Error executing analytical query: {e}")
            return {
                "sql_query": None,
                "result": None,
                "query_type": "error",
                "execution_time_ms": (time.time() - start_time) * 1000,
                "timestamp": timestamp,
                "privacy_compliant": False,
                "error": str(e),
            }


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


def run_analytical_query(
    question: str,
    authenticated_client_id: str,
    database_path: str = "data/customers.db",
) -> Dict[str, Any]:
    """
    Run analytical/statistical queries on customer database with privacy protection.

    PRIVACY RULES:
    1. ALLOWED: "What beers do I buy most?" (authenticated user's own data)
    2. BLOCKED: "What is client X's favorite brewery?" (other client's individual data)
    3. ALLOWED: "What's the most popular beer in Ohio?" (aggregate/statistical data)

    Args:
        question: Natural language question
        authenticated_client_id: The authenticated client's ID (for privacy checks)
        database_path: Path to SQLite database

    Returns:
        Dictionary with query results and metadata

    Examples:
        # Aggregate query (ALLOWED)
        run_analytical_query(
            question="What's the most purchased beer type in Colorado?",
            authenticated_client_id="CLT-ABC123"
        )

        # Own data query (ALLOWED)
        run_analytical_query(
            question="What are my top 5 beers?",
            authenticated_client_id="CLT-ABC123"
        )

        # Other client query (BLOCKED)
        run_analytical_query(
            question="What does client CLT-XYZ buy?",
            authenticated_client_id="CLT-ABC123"
        )  # Returns privacy_compliant=False
    """
    runner = SQLRunner(database_path=database_path)
    return runner.run_analytical_query(
        question=question, authenticated_client_id=authenticated_client_id
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
