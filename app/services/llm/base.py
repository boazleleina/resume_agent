from abc import ABC, abstractmethod


class LLMBase(ABC):
    @abstractmethod
    async def prompt_model(
        self,
        system_prompt: str,
        user_prompt: str,
        think: bool = False,
        model_role: str = "extraction",
    ) -> str:
        """
        Send a prompt to the model and return the response string.

        Args:
            system_prompt: Role/context instructions.
            user_prompt:   The content to process.
            think:         Enable reasoning mode if the provider supports it.
                           Providers that don't support it should ignore this flag.
            model_role:    "extraction" (fast model) or "grading" (large model).
                           Independent of think — the large model can run with
                           thinking disabled for speed.
        """
        ...
