import asyncio
import os
os.environ["MORALIS_API_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6IjVjNmI2NmFkLWQ3YmUtNDQxMS1iY2FiLWYzMDI2ZWM4NTdlZiIsIm9yZ0lkIjoiNDg5NzIxIiwidXNlcklkIjoiNTAzODU5IiwidHlwZUlkIjoiZTFhZGM2MjItYTljMS00MWJkLWI4N2MtZWI0ZjQyZWYwYWY1IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NjgxNTgxNjgsImV4cCI6NDkyMzkxODE2OH0.a7XidjregAGEXjdo_Auf-y9DgrHxLlnmFPT4LSpCrLU"

from data_sources.holder_analysis import holder_analyzer

async def test_holder():
    # Test ZORA token (non-whitelisted token from the pool)
    token = "0x1111111111166b7fe7bd91427724b487980afc69"
    result = await holder_analyzer.get_holder_analysis(token, "base")
    print(f"Source: {result.get('source')}")
    print(f"Top 10%: {result.get('top_10_percent')}")
    print(f"Holder Count: {result.get('holder_count')}")
    print(f"Concentration Risk: {result.get('concentration_risk')}")

asyncio.run(test_holder())
