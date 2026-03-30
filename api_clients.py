"""
Real API clients for GPT-4o and Claude integration in exp-001.
Replaces the simulated responses with actual API calls.
"""
import os
import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass

try:
    import openai
    import anthropic
except ImportError:
    openai = None
    anthropic = None

from circuit_breaker import Response


@dataclass
class APIConfig:
    """Configuration for API clients."""
    openai_model: str = "gpt-4o"
    claude_model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: float = 30.0


class CostEstimator:
    """Estimate API costs for experiment planning."""
    
    # Pricing per 1M tokens (as of 2024)
    OPENAI_PRICING = {
        "gpt-4o": {"input": 15.00, "output": 60.00},
        "gpt-4": {"input": 30.00, "output": 60.00}
    }
    
    ANTHROPIC_PRICING = {
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25}
    }
    
    @classmethod
    def estimate_experiment_cost(cls, runs_per_condition: int = 55, num_conditions: int = 5, 
                                avg_input_tokens: int = 150, avg_output_tokens: int = 300) -> Dict[str, float]:
        """Estimate total experiment cost."""
        total_calls = runs_per_condition * num_conditions * 2  # 2 agents per run
        
        # Estimate for mixed OpenAI/Claude usage
        openai_calls = total_calls // 2
        claude_calls = total_calls // 2
        
        # OpenAI cost
        openai_input_cost = (openai_calls * avg_input_tokens / 1_000_000) * cls.OPENAI_PRICING["gpt-4o"]["input"]
        openai_output_cost = (openai_calls * avg_output_tokens / 1_000_000) * cls.OPENAI_PRICING["gpt-4o"]["output"]
        openai_total = openai_input_cost + openai_output_cost
        
        # Claude cost
        claude_input_cost = (claude_calls * avg_input_tokens / 1_000_000) * cls.ANTHROPIC_PRICING["claude-3-sonnet-20240229"]["input"]
        claude_output_cost = (claude_calls * avg_output_tokens / 1_000_000) * cls.ANTHROPIC_PRICING["claude-3-sonnet-20240229"]["output"]
        claude_total = claude_input_cost + claude_output_cost
        
        return {
            "total_calls": total_calls,
            "openai_cost": openai_total,
            "claude_cost": claude_total,
            "total_cost": openai_total + claude_total,
            "cost_per_call": (openai_total + claude_total) / total_calls
        }


class GPTClient:
    """OpenAI GPT-4o client with circuit breaker integration."""
    
    def __init__(self, config: APIConfig):
        if openai is None:
            raise ImportError("openai package not installed. Run: pip install openai>=1.12.0")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.config = config
    
    def call_agent_a(self, task_context: str = "document_summary") -> Response:
        """Simulate Agent A: document summarization task."""
        prompt = self._get_agent_a_prompt(task_context)
        return self._make_api_call(prompt, agent_role="A")
    
    def call_agent_b(self, agent_a_output: str, task_context: str = "synthesis") -> Response:
        """Simulate Agent B: synthesis of Agent A output."""
        prompt = self._get_agent_b_prompt(agent_a_output, task_context)
        return self._make_api_call(prompt, agent_role="B")
    
    def _get_agent_a_prompt(self, task_context: str) -> str:
        """Generate prompt for Agent A (document analyzer)."""
        return f"""You are Agent A in a multi-agent system. Your role is to analyze and summarize documents.

Task: {task_context}

Please provide a comprehensive summary of the key points from the document. Focus on:
1. Main themes and concepts
2. Important details and findings
3. Conclusions or recommendations

Be thorough but concise. Indicate your confidence level in your analysis.
"""
    
    def _get_agent_b_prompt(self, agent_a_output: str, task_context: str) -> str:
        """Generate prompt for Agent B (synthesizer)."""
        return f"""You are Agent B in a multi-agent system. Your role is to synthesize information from Agent A and provide final recommendations.

Task: {task_context}

Agent A provided this analysis:
{agent_a_output}

Based on Agent A's work, please:
1. Synthesize the key insights
2. Provide actionable recommendations
3. Identify any gaps or areas needing further analysis

Provide your final assessment and confidence level.
"""
    
    def _make_api_call(self, prompt: str, agent_role: str) -> Response:
        """Make the actual API call to GPT-4o with retry logic."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[
                        {"role": "system", "content": f"You are Agent {agent_role} in an AI reliability experiment."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.timeout
                )
                
                elapsed = time.time() - start_time
                content = response.choices[0].message.content or ""
                
                # Extract confidence from response or estimate based on response quality
                confidence = self._estimate_confidence(content, elapsed)
                
                # Token usage (approximation if not available)
                token_usage = getattr(response.usage, 'total_tokens', len(content.split()) * 1.3)
                
                return Response(
                    content=content,
                    confidence=confidence,
                    token_usage=int(token_usage),
                    reasoning=f"GPT-4o response from Agent {agent_role} (took {elapsed:.2f}s, attempt {attempt + 1})"
                )
                
            except openai.APITimeoutError:
                if attempt == max_retries - 1:
                    raise TimeoutError("GPT-4o API timeout after retries")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            except openai.RateLimitError:
                if attempt == max_retries - 1:
                    raise Exception("GPT-4o rate limit exceeded after retries")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"GPT-4o API error after retries: {str(e)}")
                time.sleep(retry_delay)
    
    def _estimate_confidence(self, content: str, response_time: float) -> float:
        """Estimate confidence based on response characteristics."""
        # Base confidence on response length, speed, and content quality indicators
        content_lower = content.lower()
        
        # Confidence indicators
        low_confidence_markers = [
            "i'm not sure", "i don't know", "uncertain", "might be", "possibly",
            "i cannot be certain", "it's unclear", "hard to say"
        ]
        high_confidence_markers = [
            "clearly", "definitely", "certainly", "confident that", "evident",
            "obvious", "without doubt", "undoubtedly"
        ]
        
        # Start with base confidence
        confidence = 0.7
        
        # Adjust based on markers
        for marker in low_confidence_markers:
            if marker in content_lower:
                confidence -= 0.2
                break
        
        for marker in high_confidence_markers:
            if marker in content_lower:
                confidence += 0.1
                break
        
        # Adjust based on response time (very fast or very slow might indicate issues)
        if response_time < 1.0:
            confidence -= 0.1  # Too fast might be superficial
        elif response_time > 20.0:
            confidence -= 0.15  # Too slow might indicate difficulty
        
        # Adjust based on length (very short responses might be incomplete)
        if len(content) < 50:
            confidence -= 0.2
        elif len(content) > 500:
            confidence += 0.1
        
        return max(0.1, min(0.95, confidence))


class ClaudeClient:
    """Anthropic Claude client with circuit breaker integration."""
    
    def __init__(self, config: APIConfig):
        if anthropic is None:
            raise ImportError("anthropic package not installed. Run: pip install anthropic>=0.18.0")
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.config = config
    
    def call_agent_a(self, task_context: str = "document_summary") -> Response:
        """Simulate Agent A: document summarization task."""
        prompt = self._get_agent_a_prompt(task_context)
        return self._make_api_call(prompt, agent_role="A")
    
    def call_agent_b(self, agent_a_output: str, task_context: str = "synthesis") -> Response:
        """Simulate Agent B: synthesis of Agent A output."""
        prompt = self._get_agent_b_prompt(agent_a_output, task_context)
        return self._make_api_call(prompt, agent_role="B")
    
    def _get_agent_a_prompt(self, task_context: str) -> str:
        """Generate prompt for Agent A (document analyzer)."""
        return f"""You are Agent A in a multi-agent system focused on document analysis and summarization.

Your task: {task_context}

Please analyze the provided information and create a comprehensive summary that includes:

1. **Key Findings**: What are the most important discoveries or insights?
2. **Supporting Details**: What evidence supports these findings?
3. **Implications**: What do these findings mean in the broader context?

Please provide your analysis with clear reasoning and indicate your confidence level in your conclusions.
"""
    
    def _get_agent_b_prompt(self, agent_a_output: str, task_context: str) -> str:
        """Generate prompt for Agent B (synthesizer)."""
        return f"""You are Agent B in a multi-agent collaborative system. Your role is to synthesize and build upon Agent A's work.

Context: {task_context}

Agent A has provided this analysis:

<agent_a_output>
{agent_a_output}
</agent_a_output>

Your task is to:

1. **Synthesize**: Integrate Agent A's findings into a coherent framework
2. **Extend**: Add additional insights or perspectives where appropriate
3. **Recommend**: Provide actionable recommendations based on the combined analysis
4. **Validate**: Assess the quality and completeness of the overall analysis

Please provide your synthesis with clear reasoning about your confidence in the final recommendations.
"""
    
    def _make_api_call(self, prompt: str, agent_role: str) -> Response:
        """Make the actual API call to Claude with retry logic."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.client.messages.create(
                    model=self.config.claude_model,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    timeout=self.config.timeout
                )
                
                elapsed = time.time() - start_time
                content = response.content[0].text if response.content else ""
                
                # Extract confidence from response or estimate based on response quality
                confidence = self._estimate_confidence(content, elapsed)
                
                # Token usage estimation (Claude doesn't always provide exact counts)
                token_usage = getattr(response.usage, 'output_tokens', len(content.split()) * 1.3)
                if hasattr(response.usage, 'input_tokens'):
                    token_usage += response.usage.input_tokens
                
                return Response(
                    content=content,
                    confidence=confidence,
                    token_usage=int(token_usage),
                    reasoning=f"Claude response from Agent {agent_role} (took {elapsed:.2f}s, attempt {attempt + 1})"
                )
                
            except anthropic.APITimeoutError:
                if attempt == max_retries - 1:
                    raise TimeoutError("Claude API timeout after retries")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            except anthropic.RateLimitError:
                if attempt == max_retries - 1:
                    raise Exception("Claude rate limit exceeded after retries")
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Claude API error after retries: {str(e)}")
                time.sleep(retry_delay)
    
    def _estimate_confidence(self, content: str, response_time: float) -> float:
        """Estimate confidence based on response characteristics."""
        content_lower = content.lower()
        
        # Claude-specific confidence indicators
        low_confidence_markers = [
            "i'm uncertain", "i cannot be sure", "it's difficult to determine",
            "i don't have enough information", "i'm not confident", "it's unclear",
            "i cannot determine", "it's hard to say"
        ]
        high_confidence_markers = [
            "i'm confident", "clearly", "definitely", "certainly", "it's evident",
            "without doubt", "it's clear that", "undoubtedly", "i can confidently say"
        ]
        
        # Start with base confidence
        confidence = 0.75  # Claude typically more verbose/thoughtful
        
        # Adjust based on markers
        for marker in low_confidence_markers:
            if marker in content_lower:
                confidence -= 0.25
                break
        
        for marker in high_confidence_markers:
            if marker in content_lower:
                confidence += 0.1
                break
        
        # Adjust based on response time
        if response_time < 2.0:
            confidence -= 0.1  # Too fast might be superficial
        elif response_time > 25.0:
            confidence -= 0.1  # Too slow might indicate difficulty
        
        # Adjust based on structure (Claude tends to be well-structured when confident)
        if "1." in content and "2." in content:
            confidence += 0.05  # Structured response
        
        if len(content) < 100:
            confidence -= 0.2  # Very short might be incomplete
        elif len(content) > 800:
            confidence += 0.05  # Comprehensive response
        
        return max(0.1, min(0.95, confidence))


class APIClientFactory:
    """Factory for creating API clients based on configuration."""
    
    @staticmethod
    def create_gpt_client(config: Optional[APIConfig] = None) -> GPTClient:
        """Create a GPT client with the given configuration."""
        if config is None:
            config = APIConfig()
        return GPTClient(config)
    
    @staticmethod
    def create_claude_client(config: Optional[APIConfig] = None) -> ClaudeClient:
        """Create a Claude client with the given configuration."""
        if config is None:
            config = APIConfig()
        return ClaudeClient(config)
    
    @staticmethod
    def is_openai_available() -> bool:
        """Check if OpenAI API key is available."""
        return bool(os.getenv("OPENAI_API_KEY"))
    
    @staticmethod
    def is_anthropic_available() -> bool:
        """Check if Anthropic API key is available."""
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    
    @staticmethod
    def get_available_clients(config: Optional[APIConfig] = None):
        """Get available client types based on API keys."""
        available = []
        if APIClientFactory.is_openai_available():
            available.append('gpt')
        if APIClientFactory.is_anthropic_available():
            available.append('claude')
        return available