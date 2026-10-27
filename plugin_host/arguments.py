from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SafeFileReaderArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_path: str = Field(min_length=1, max_length=240)


class CalculatorArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str = Field(min_length=1, max_length=256)


PYDANTIC_ARGUMENT_MODELS: dict[str, type[BaseModel]] = {
    "safe_file_reader": SafeFileReaderArgs,
    "secure_calculator": CalculatorArgs,
}


def validate_with_pydantic(tool_name: str, arguments: Any) -> dict[str, Any] | None:
    """Use concrete Pydantic models for built-ins; return None for extensions."""
    model = PYDANTIC_ARGUMENT_MODELS.get(tool_name)
    if model is None:
        return None
    return model.model_validate(arguments).model_dump()
