"""Tools for collaborative reasoning between Tiled, RPGJS, and Pydantic agents."""
from typing import Dict, Any, Optional, List
import logging
import httpx
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from httpx import RequestError, HTTPError, TimeoutException

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

class AgentCommunication:
    """Enables collaborative problem-solving between Railway agents."""
    
    def __init__(self) -> None:
        """Initialize agent communication with API endpoints."""
        logger.info("Initializing AgentCommunication")
        self.rpgjs_api_url: str = os.getenv(
            "RPGJS_API_URL", 
            "https://rpgjs-agent-api-production.up.railway.app"
        )
        self.pydantic_api_url: str = os.getenv(
            "PYDANTIC_API_URL", 
            "https://crawl4ai-api-production.up.railway.app"
        )
        self.api_bearer_token: str = os.getenv(
            "API_BEARER_TOKEN", 
            "UI7m8MUBXNxxm3MMMC00BPP7/QEpnFPH/Thbmm9oWqg="
        ).strip()

        self.headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.debug(f"Using RPGJS API URL: {self.rpgjs_api_url}")
        logger.debug(f"Using Pydantic API URL: {self.pydantic_api_url}")

    async def _retry_request(
        self, 
        client: httpx.AsyncClient, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """Retry HTTP requests with exponential backoff."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1} for {method} {url}")
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except TimeoutException as te:
                logger.warning(f"Timeout on attempt {attempt+1} for {url}: {te}")
                if attempt == max_retries - 1:
                    raise
            except HTTPError as he:
                logger.error(f"HTTP error for {url}: {he}")
                raise
            except RequestError as re:
                logger.error(f"Request error for {url}: {re}")
                raise
        raise RuntimeError(f"Failed after {max_retries} attempts")

    # Query templates for different agent types
    RPGJS_QUERY_TEMPLATES = {
        "npc_behavior": (
            "How should the map be structured to support AI-NPCs in RPGJS? "
            "Specifically:\n"
            "- Required event layers\n"
            "- NPC movement areas\n"
            "- Interaction zones\n"
            "- Event triggers\n"
            "- Custom properties for AI behavior\n"
            "{user_input}"
        ),
        "environmental_factors": (
            "What map elements affect NPC behavior in RPGJS?\n"
            "Include:\n"
            "- Tile properties that affect NPCs\n"
            "- Event system integration\n"
            "- Collision handling\n"
            "- Area triggers\n"
            "{user_input}"
        )
    }

    PYDANTIC_QUERY_TEMPLATES = {
        "npc_schema": (
            "Design a schema for AI-NPC properties in a Tiled map:\n"
            "- Environmental influence factors\n"
            "- Behavior parameters\n"
            "- State management\n"
            "- Event triggers\n"
            "{user_input}"
        ),
        "map_validation": (
            "Create validation rules for RPGJS map requirements:\n"
            "- Layer structure\n"
            "- Required properties\n"
            "- Event format\n"
            "- NPC configuration\n"
            "{user_input}"
        )
    }

    def get_rpgjs_query(self, query_type: str, user_input: str = "") -> str:
        """Get a formatted RPGJS query template."""
        template = self.RPGJS_QUERY_TEMPLATES.get(query_type)
        if not template:
            logger.warning(f"Unknown RPGJS query type: {query_type}")
            return user_input
        return template.format(user_input=f"User input: {user_input}" if user_input else "")

    def get_pydantic_query(self, query_type: str, user_input: str = "") -> str:
        """Get a formatted Pydantic query template."""
        template = self.PYDANTIC_QUERY_TEMPLATES.get(query_type)
        if not template:
            logger.warning(f"Unknown Pydantic query type: {query_type}")
            return user_input
        return template.format(user_input=f"User input: {user_input}" if user_input else "")

    async def analyze_request(self, user_request: str) -> Dict[str, List[str]]:
        """Break down a complex user request into components for each agent."""
        logger.info(f"Analyzing request: {user_request[:100]}...")
        aspects: Dict[str, List[str]] = {
            "tiled_aspects": [],
            "rpgjs_aspects": [],
            "pydantic_aspects": []
        }
        
        if "ai" in user_request.lower() and "npc" in user_request.lower():
            aspects["tiled_aspects"].extend([
                "environmental_factors",
                "event_triggers",
                "object_placement",
                "custom_properties"
            ])
            aspects["rpgjs_aspects"].extend([
                "npc_behavior",
                "event_handling",
                "ai_integration"
            ])
            aspects["pydantic_aspects"].extend([
                "npc_schema",
                "behavior_models",
                "environmental_rules"
            ])
            logger.debug("Found AI-NPC related aspects in request")
        else:
            logger.info("Request does not contain AI-NPC keywords")
        
        return aspects

    async def ask_rpgjs_agent(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Query the RPGJS agent with context-aware questions."""
        endpoint = f"{self.rpgjs_api_url}/api/ask"
        
        payload = {
            "query": query,
            "user_id": "tiled_agent",
            "session_id": str(int(datetime.now().timestamp())),
            "context": str(context) if context else None
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await self._retry_request(
                    client,
                    "POST",
                    endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                return response.json()
        except Exception as e:
            logger.error(f"Failed to communicate with RPGJS agent: {e}")
            return {
                "error": str(e),
                "message": "Failed to communicate with RPGJS agent"
            }
    
    async def ask_pydantic_agent(self, query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Query the Pydantic agent with context-aware questions."""
        endpoint = f"{self.pydantic_api_url}/api/ask"
        
        payload = {
            "query": query,
            "user_id": "tiled_agent",
            "session_id": str(int(datetime.now().timestamp())),
            "context": str(context) if context else None
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await self._retry_request(
                    client,
                    "POST",
                    endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                return response.json()["response"] if "response" in response.json() else response.json()
        except Exception as e:
            logger.error(f"Failed to communicate with Pydantic agent: {e}")
            return {
                "error": str(e),
                "message": "Failed to communicate with Pydantic agent"
            }
    
    async def collaborative_map_design(self, user_request: str) -> Dict[str, Any]:
        """Coordinate between agents to design a map meeting complex requirements."""
        logger.info("Starting collaborative map design process")
        aspects = await self.analyze_request(user_request)

        # Get RPGJS insights
        rpgjs_responses: Dict[str, Any] = {}
        rpgjs_context = {
            "request_type": "map_design",
            "aspects": aspects["rpgjs_aspects"],
            "original_request": user_request
        }

        for query_type in ["npc_behavior", "environmental_factors"]:
            query = self.get_rpgjs_query(query_type, user_request)
            rpgjs_responses[query_type] = await self.ask_rpgjs_agent(
                query, 
                context=rpgjs_context
            )

        # Get Pydantic insights
        pydantic_responses: Dict[str, Any] = {}
        pydantic_context = {
            "request_type": "npc_modeling",
            "aspects": aspects["pydantic_aspects"],
            "rpgjs_requirements": rpgjs_responses,
            "original_request": user_request
        }

        for query_type in ["npc_schema", "map_validation"]:
            query = self.get_pydantic_query(query_type, user_request)
            pydantic_responses[query_type] = await self.ask_pydantic_agent(
                query, 
                context=pydantic_context
            )

        logger.info("Synthesizing map design recommendations")
        return {
            "analysis": aspects,
            "rpgjs_insights": rpgjs_responses,
            "pydantic_insights": pydantic_responses,
            "map_recommendations": {
                "layers": self._derive_layer_structure(rpgjs_responses, pydantic_responses),
                "properties": self._derive_custom_properties(rpgjs_responses, pydantic_responses),
                "events": self._derive_event_structure(rpgjs_responses, pydantic_responses)
            }
        }
    
    def _derive_layer_structure(
        self,
        rpgjs_data: Dict[str, Any],
        pydantic_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Derive optimal layer structure based on agent responses."""
        logger.debug("Deriving layer structure from agent responses")
        
        # Base layer structure
        layers: List[Dict[str, Any]] = [
            {
                "name": "Ground",
                "type": "tilelayer",
                "properties": {}
            },
            {
                "name": "Environment",
                "type": "tilelayer",
                "properties": {
                    "affects_npc_behavior": True
                }
            },
            {
                "name": "NPCs",
                "type": "objectgroup",
                "properties": {
                    "ai_controlled": True
                }
            },
            {
                "name": "Events",
                "type": "objectgroup",
                "properties": {
                    "event_type": "ai_trigger"
                }
            }
        ]

        # Validate layer names
        layer_names = {layer["name"] for layer in layers}
        if len(layer_names) != len(layers):
            logger.warning("Duplicate layer names detected in layer structure")

        return layers

    def _derive_custom_properties(
        self,
        rpgjs_data: Dict[str, Any],
        pydantic_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Derive custom properties based on agent responses."""
        logger.debug("Deriving custom properties from agent responses")
        
        # Base properties structure
        properties: List[Dict[str, Any]] = [
            {
                "name": "environmental_factor",
                "type": "string",
                "values": ["peaceful", "hostile", "neutral"]
            },
            {
                "name": "npc_behavior_zone",
                "type": "string",
                "values": ["patrol", "guard", "wander", "interact"]
            },
            {
                "name": "interaction_type",
                "type": "string",
                "values": ["quest", "shop", "dialogue", "battle"]
            }
        ]

        # Validate property names
        property_names = {prop["name"] for prop in properties}
        if len(property_names) != len(properties):
            logger.warning("Duplicate property names detected in custom properties")

        return properties

    def _derive_event_structure(
        self,
        rpgjs_data: Dict[str, Any],
        pydantic_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Derive event structure based on agent responses."""
        logger.debug("Deriving event structure from agent responses")
        
        # Base event structure
        events: List[Dict[str, Any]] = [
            {
                "type": "npc_spawn",
                "properties": {
                    "ai_type": "string",
                    "behavior_params": "json",
                    "interaction_radius": "number"
                }
            },
            {
                "type": "environment_trigger",
                "properties": {
                    "effect": "string",
                    "duration": "number",
                    "radius": "number"
                }
            },
            {
                "type": "behavior_modifier",
                "properties": {
                    "modifier_type": "string",
                    "strength": "number",
                    "conditions": "json"
                }
            }
        ]

        # Validate event types
        event_types = {event["type"] for event in events}
        if len(event_types) != len(events):
            logger.warning("Duplicate event types detected in event structure")

        return events
