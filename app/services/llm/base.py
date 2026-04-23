from abc import ABC, abstractmethod


class LLMBase(ABC):
    @abstractmethod
    async def prompt_model(
        self,
        system_prompt: str,
        user_prompt: str,
        think: bool = False,
    ) -> str:
        """
        Send a prompt to the model and return the response string.

        Args:
            system_prompt: Role/context instructions.
            user_prompt:   The content to process.
            think:         Enable reasoning mode if the provider supports it.
                           Providers that don't support it should ignore this flag.
        """
        ...
