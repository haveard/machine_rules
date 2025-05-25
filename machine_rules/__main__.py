# machine_rules/__main__.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import the main package to ensure initialization
import machine_rules  # noqa: F401
from machine_rules.api.registry import RuleServiceProviderManager


class FactModel(BaseModel):
    facts: list
    ruleset_uri: str


app = FastAPI()


@app.post("/execute")
def execute_rule_set(data: FactModel):
    try:
        provider = RuleServiceProviderManager.get("api")
        if not provider:
            detail = "No rule service provider registered for 'api'"
            raise HTTPException(status_code=500, detail=detail)

        runtime = provider.get_rule_runtime()
        session = runtime.create_rule_session(
            data.ruleset_uri, {}, stateless=True
        )
        session.add_facts(data.facts)
        results = session.execute()
        session.close()

        return {"results": results}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        detail = f"Internal server error: {str(e)}"
        raise HTTPException(status_code=500, detail=detail)


if __name__ == "__main__":
    uvicorn.run(
        "machine_rules.__main__:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
