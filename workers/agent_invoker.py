"""
Agent Invoker - Calls Manus/Claude API to execute agent tasks
"""
import os
import json
import httpx
from typing import Dict, Any, Optional
from anthropic import Anthropic

# API Configuration
API_PROVIDER = os.getenv("API_PROVIDER", "manus")  # manus or claude
MANUS_API_KEY = os.getenv("MANUS_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
MANUS_API_BASE = os.getenv("MANUS_API_BASE", "https://api.manus.im/v1")


class AgentInvoker:
    """Handles invocation of AI agents via API"""
    
    def __init__(self):
        self.provider = API_PROVIDER
        if self.provider == "claude":
            self.client = Anthropic(api_key=CLAUDE_API_KEY)
        else:
            self.api_key = MANUS_API_KEY
            self.api_base = MANUS_API_BASE
    
    def load_prompt(self, agent_name: str) -> str:
        """Load agent prompt from file"""
        prompt_path = f"/app/agents/{agent_name}/prompt.md"
        try:
            with open(prompt_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(f"Prompt file not found for agent: {agent_name}")
    
    def inject_story_data(self, prompt_template: str, story_data: Dict[str, Any]) -> str:
        """Inject story data into prompt template"""
        # Simple template variable replacement
        prompt = prompt_template.replace("{{story.id}}", story_data.get("story_id", ""))
        prompt = prompt.replace("{{story.title}}", story_data.get("title", ""))
        prompt = prompt.replace("{{story.description}}", story_data.get("description", ""))
        
        # Handle acceptance criteria (list)
        criteria = story_data.get("acceptance_criteria", [])
        if isinstance(criteria, str):
            try:
                criteria = json.loads(criteria)
            except:
                criteria = [criteria]
        
        criteria_text = "\n".join([f"- {c}" for c in criteria])
        prompt = prompt.replace("{{#each story.acceptanceCriteria}}\n- {{this}}\n{{/each}}", criteria_text)
        
        return prompt
    
    async def invoke_agent(
        self,
        agent_name: str,
        story_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an agent to process a story
        
        Args:
            agent_name: Name of the agent (backend, mobile, qa, code_review, security)
            story_data: Story data
            context: Additional context (AGENTS.md, progress.txt, etc.)
        
        Returns:
            Agent response with file modifications and learnings
        """
        # Load and prepare prompt
        prompt_template = self.load_prompt(agent_name)
        prompt = self.inject_story_data(prompt_template, story_data)
        
        # Add context if provided
        if context:
            agents_md = context.get("agents_md", "")
            progress_txt = context.get("progress_txt", "")
            
            if agents_md:
                prompt += f"\n\n## Project Knowledge Base (AGENTS.md)\n\n{agents_md}"
            if progress_txt:
                prompt += f"\n\n## Recent Learnings (progress.txt)\n\n{progress_txt}"
        
        # Call API based on provider
        if self.provider == "claude":
            return await self._call_claude(prompt)
        else:
            return await self._call_manus(prompt)
    
    async def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Call Claude API"""
        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            
            # Parse JSON response
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                return {
                    "error": "Failed to parse agent response as JSON",
                    "raw_response": response_text
                }
        
        except Exception as e:
            return {
                "error": str(e),
                "raw_response": None
            }
    
    async def _call_manus(self, prompt: str) -> Dict[str, Any]:
        """Call Manus API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
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
                try:
                    # Extract JSON from markdown code blocks if present
                    if "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    result = json.loads(response_text)
                    return result
                except json.JSONDecodeError:
                    return {
                        "error": "Failed to parse agent response as JSON",
                        "raw_response": response_text
                    }
        
        except Exception as e:
            return {
                "error": str(e),
                "raw_response": None
            }


# Global invoker instance
invoker = AgentInvoker()
