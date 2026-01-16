"""
Agent Invoker - Calls Manus/Claude API to execute agent tasks
Supports loading prompts from database with filesystem fallback
Supports loading API keys from database settings
"""
import os
import sys
import json
import httpx
from typing import Dict, Any, Optional
from anthropic import Anthropic

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API Configuration (defaults - can be overridden by database settings)
API_PROVIDER = os.getenv("API_PROVIDER", "claude")  # manus or claude
MANUS_API_KEY = os.getenv("MANUS_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
MANUS_API_BASE = os.getenv("MANUS_API_BASE", "https://api.manus.im/v1")

# Prompt file base path
PROMPT_BASE_PATH = os.getenv("PROMPT_BASE_PATH", "/app/agents")


def get_api_settings_from_db(db_session) -> Dict[str, str]:
    """
    Load API settings from database.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Dict with api_provider, claude_api_key, manus_api_key
    """
    settings = {}
    try:
        from orchestrator.models import SystemSetting
        from orchestrator.crypto import decrypt_value

        for key in ["api_provider", "claude_api_key", "manus_api_key"]:
            setting = db_session.query(SystemSetting).filter(
                SystemSetting.key == key
            ).first()
            if setting and setting.value:
                if setting.is_encrypted:
                    try:
                        settings[key] = decrypt_value(setting.value)
                    except Exception:
                        settings[key] = ""
                else:
                    settings[key] = setting.value
    except Exception as e:
        print(f"Warning: Failed to load API settings from DB: {e}")

    return settings


class AgentInvoker:
    """Handles invocation of AI agents via API with database-backed prompts"""

    def __init__(self, db_session=None):
        # Default to environment variables
        self.provider = API_PROVIDER
        self.claude_api_key = CLAUDE_API_KEY
        self.manus_api_key = MANUS_API_KEY
        self.api_base = MANUS_API_BASE
        self.client = None

        # Override with database settings if available
        if db_session:
            self._load_settings_from_db(db_session)

        # Initialize client based on provider
        self._init_client()

    def _load_settings_from_db(self, db_session):
        """Load API settings from database"""
        settings = get_api_settings_from_db(db_session)
        if settings.get("api_provider"):
            self.provider = settings["api_provider"]
        if settings.get("claude_api_key"):
            self.claude_api_key = settings["claude_api_key"]
        if settings.get("manus_api_key"):
            self.manus_api_key = settings["manus_api_key"]

    def _init_client(self):
        """Initialize API client based on provider"""
        if self.provider == "claude" and self.claude_api_key:
            self.client = Anthropic(api_key=self.claude_api_key)

    def load_prompt(self, agent_name: str, db_session=None) -> str:
        """
        Load agent prompt from database with filesystem fallback.

        Args:
            agent_name: Name of the agent (backend, mobile, qa, code_review, security)
            db_session: SQLAlchemy database session (optional)

        Returns:
            Prompt content as string
        """
        # Try database first if session provided
        if db_session is not None:
            try:
                prompt = self._load_prompt_from_db(agent_name, db_session)
                if prompt:
                    return prompt
            except Exception as e:
                # Log error but continue to filesystem fallback
                print(f"Warning: Failed to load prompt from DB: {e}")

        # Fallback to filesystem
        return self._load_prompt_from_file(agent_name)

    def _load_prompt_from_db(self, agent_name: str, db_session) -> Optional[str]:
        """
        Load prompt from database.

        Args:
            agent_name: Name of the agent
            db_session: SQLAlchemy session

        Returns:
            Prompt content or None if not found
        """
        try:
            from orchestrator.models import AgentPrompt

            # Get the active prompt for this agent (latest version)
            prompt = db_session.query(AgentPrompt).filter(
                AgentPrompt.agent_name == agent_name,
                AgentPrompt.is_active == True
            ).order_by(AgentPrompt.version.desc()).first()

            if prompt:
                return prompt.content

            return None
        except ImportError:
            # Models not available
            return None

    def _load_prompt_from_file(self, agent_name: str) -> str:
        """
        Load prompt from filesystem.

        Args:
            agent_name: Name of the agent

        Returns:
            Prompt content

        Raises:
            ValueError: If prompt file not found
        """
        prompt_path = os.path.join(PROMPT_BASE_PATH, agent_name, "prompt.md")
        try:
            with open(prompt_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Prompt file not found for agent: {agent_name} at {prompt_path}")

    def inject_story_data(self, prompt_template: str, story_data: Dict[str, Any]) -> str:
        """
        Inject story data into prompt template.
        Supports both {{variable}} and {{#each}} syntax.

        Args:
            prompt_template: The prompt template with placeholders
            story_data: Story data to inject

        Returns:
            Populated prompt string
        """
        prompt = prompt_template

        # Simple variable replacements
        prompt = prompt.replace("{{story.id}}", str(story_data.get("story_id", "")))
        prompt = prompt.replace("{{story.title}}", str(story_data.get("title", "")))
        prompt = prompt.replace("{{story.description}}", str(story_data.get("description", "")))

        # Handle acceptance criteria (list)
        criteria = story_data.get("acceptance_criteria", [])
        if isinstance(criteria, str):
            try:
                criteria = json.loads(criteria)
            except (json.JSONDecodeError, TypeError):
                criteria = [criteria] if criteria else []

        criteria_text = "\n".join([f"- {c}" for c in criteria])

        # Replace handlebars-style each block
        prompt = prompt.replace(
            "{{#each story.acceptanceCriteria}}\n- {{this}}\n{{/each}}",
            criteria_text
        )

        # Also handle simpler format
        prompt = prompt.replace("{{story.acceptanceCriteria}}", criteria_text)

        # Handle file changes for review/qa agents
        file_changes = story_data.get("file_changes", [])
        if isinstance(file_changes, str):
            try:
                file_changes = json.loads(file_changes)
            except (json.JSONDecodeError, TypeError):
                file_changes = []

        if file_changes:
            files_text = "\n".join([
                f"- {f.get('path', 'unknown')} ({f.get('action', 'unknown')})"
                for f in file_changes
            ])
            prompt = prompt.replace(
                "{{#each story.file_changes}}\n- {{this.path}} ({{this.action}})\n{{/each}}",
                files_text
            )

        # Handle dependencies
        dependencies = story_data.get("dependencies", [])
        if isinstance(dependencies, str):
            try:
                dependencies = json.loads(dependencies)
            except (json.JSONDecodeError, TypeError):
                dependencies = []

        if dependencies:
            deps_text = ", ".join(dependencies)
            prompt = prompt.replace("{{story.dependencies}}", deps_text)

        return prompt

    async def invoke_agent(
        self,
        agent_name: str,
        story_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        db_session=None
    ) -> Dict[str, Any]:
        """
        Invoke an agent to process a story.

        Args:
            agent_name: Name of the agent (backend, mobile, qa, code_review, security)
            story_data: Story data including title, description, acceptance_criteria
            context: Additional context (AGENTS.md, progress.txt, codebase info)
            db_session: Database session for loading prompts from DB

        Returns:
            Agent response with file modifications and learnings
        """
        # Load and prepare prompt
        prompt_template = self.load_prompt(agent_name, db_session)
        prompt = self.inject_story_data(prompt_template, story_data)

        # Add context if provided
        if context:
            # Project knowledge base
            agents_md = context.get("agents_md", "")
            if agents_md:
                prompt += f"\n\n## Project Knowledge Base (AGENTS.md)\n\n{agents_md}"

            # Recent learnings
            progress_txt = context.get("progress_txt", "")
            if progress_txt:
                prompt += f"\n\n## Recent Learnings (progress.txt)\n\n{progress_txt}"

            # Codebase information
            codebase_info = context.get("codebase_info")
            if codebase_info:
                prompt += f"\n\n## Codebase Information\n\n"
                prompt += f"- Framework: {codebase_info.get('framework', 'Unknown')}\n"
                prompt += f"- Language: {codebase_info.get('language', 'Unknown')}\n"
                prompt += f"- Build Command: {codebase_info.get('build_command', 'N/A')}\n"
                prompt += f"- Test Command: {codebase_info.get('test_command', 'N/A')}\n"

        # Call API based on provider
        if self.provider == "claude":
            return await self._call_claude(prompt)
        else:
            return await self._call_manus(prompt)

    async def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Call Claude API"""
        try:
            if not self.client:
                if not self.claude_api_key:
                    return {
                        "error": "Claude API key not configured. Please set it in Settings.",
                        "raw_response": None
                    }
                self.client = Anthropic(api_key=self.claude_api_key)

            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Parse JSON response
            return self._parse_response(response_text)

        except Exception as e:
            return {
                "error": str(e),
                "raw_response": None
            }

    async def _call_manus(self, prompt: str) -> Dict[str, Any]:
        """Call Manus API"""
        try:
            if not self.manus_api_key:
                return {
                    "error": "Manus API key not configured. Please set it in Settings.",
                    "raw_response": None
                }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.manus_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4.1-mini",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 8000
                    },
                    timeout=300.0  # 5 minute timeout
                )

                response.raise_for_status()
                data = response.json()

                response_text = data["choices"][0]["message"]["content"]

                # Parse JSON response
                return self._parse_response(response_text)

        except Exception as e:
            return {
                "error": str(e),
                "raw_response": None
            }

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse agent response, extracting JSON from markdown code blocks if needed.

        Args:
            response_text: Raw response from AI

        Returns:
            Parsed JSON dict or error dict
        """
        try:
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                # Try generic code block
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    potential_json = response_text[json_start:json_end].strip()
                    # Check if it looks like JSON
                    if potential_json.startswith("{") or potential_json.startswith("["):
                        response_text = potential_json

            result = json.loads(response_text)
            return result

        except json.JSONDecodeError:
            return {
                "error": "Failed to parse agent response as JSON",
                "raw_response": response_text
            }


def get_invoker(db_session=None) -> AgentInvoker:
    """
    Get an AgentInvoker instance, optionally with database settings.

    Args:
        db_session: SQLAlchemy database session for loading settings from DB

    Returns:
        AgentInvoker instance
    """
    return AgentInvoker(db_session=db_session)


# Global invoker instance (uses env vars only, for backward compatibility)
invoker = AgentInvoker()
