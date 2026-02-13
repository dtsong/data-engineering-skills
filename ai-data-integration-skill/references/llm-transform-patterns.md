# LLM Transform Patterns Reference

> LLM-powered data enrichment, classification, and extraction with cost awareness. Part of the [AI Data Integration Skill](../SKILL.md).

---

## When LLM Transforms Make Sense

### Cost-Benefit Decision Framework

```
Is the transform on structured data with clear rules?
├── Yes → Use traditional code (regex, lookup tables, rules)
└── No → Does it require understanding natural language?
    ├── No → Use traditional ML (sklearn, etc.)
    └── Yes → Does it need world knowledge or reasoning?
        ├── No → Use fine-tuned small model or embeddings
        └── Yes → Use LLM transform (with cost guardrails)
```

**Cost reality check:**

| Operation | Traditional Cost | LLM Cost | LLM Worth It? |
|-----------|-----------------|----------|---------------|
| Categorize by keyword rules | ~$0 | ~$0.01/row | No |
| Classify free-text sentiment | ~$0.001/row (ML model) | ~$0.005/row | Maybe (if accuracy matters) |
| Extract entities from unstructured text | ~$0.01/row (NER model) | ~$0.005/row | Yes (more flexible) |
| Resolve ambiguous entity matches | Hard to automate | ~$0.01/row | Yes |
| Summarize long text | Not possible traditionally | ~$0.01/row | Yes (unique LLM capability) |
| Enrich with world knowledge | Not possible | ~$0.01/row | Yes (unique LLM capability) |

---

## Batch Processing Pattern

Always process records in batches — never one LLM call per row.

```python
import anthropic
import json
from pydantic import BaseModel
from typing import Literal

class ClassifiedRecord(BaseModel):
    id: str
    category: Literal["bug", "feature", "question", "docs", "other"]
    confidence: float
    reasoning: str

def classify_batch(
    records: list[dict],
    batch_size: int = 25,
    model: str = "claude-haiku-4-5-20251001",
) -> list[ClassifiedRecord]:
    """
    Batch classification — one LLM call per batch, not per record.

    Cost: ~$0.01 per batch of 25 (vs $0.25 if done per-record)
    """
    client = anthropic.Anthropic()
    results = []

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        # Format batch compactly
        items = "\n".join(
            f"[{r['id']}] {r['title']}: {r.get('description', '')[:150]}"
            for r in batch
        )

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system="""Classify each item. Return JSON array:
[{"id": "...", "category": "bug|feature|question|docs|other", "confidence": 0.0-1.0, "reasoning": "brief reason"}]

Only output the JSON array, nothing else.""",
            messages=[{"role": "user", "content": items}],
        )

        batch_results = json.loads(response.content[0].text)
        for r in batch_results:
            results.append(ClassifiedRecord.model_validate(r))

    return results
```

---

## Entity Extraction

```python
from pydantic import BaseModel
from typing import Optional

class ExtractedEntity(BaseModel):
    company_name: Optional[str] = None
    person_name: Optional[str] = None
    dollar_amount: Optional[float] = None
    date_reference: Optional[str] = None
    product_name: Optional[str] = None

def extract_entities_batch(
    texts: list[dict],
    batch_size: int = 20,
) -> list[dict]:
    """Extract structured entities from unstructured text."""
    client = anthropic.Anthropic()
    results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        items = "\n---\n".join(
            f"[{t['id']}] {t['text'][:500]}" for t in batch
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system="""Extract entities from each text block. Return JSON array:
[{"id": "...", "company_name": "...", "person_name": "...", "dollar_amount": ..., "date_reference": "...", "product_name": "..."}]
Use null for fields not found. Only output JSON.""",
            messages=[{"role": "user", "content": items}],
        )

        batch_results = json.loads(response.content[0].text)
        for r in batch_results:
            validated = ExtractedEntity.model_validate(r)
            results.append({"id": r["id"], **validated.model_dump()})

    return results
```

---

## Structured Output with Tool Use

Use Claude's tool use for reliable structured output:

```python
import anthropic

def classify_with_tools(text: str) -> dict:
    """Use tool use for guaranteed structured output."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=[{
            "name": "classify_text",
            "description": "Classify the given text into a category",
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["bug", "feature", "question", "docs", "other"],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "reasoning": {
                        "type": "string",
                        "maxLength": 200,
                    },
                },
                "required": ["category", "confidence", "reasoning"],
            },
        }],
        tool_choice={"type": "tool", "name": "classify_text"},
        messages=[{"role": "user", "content": f"Classify this text:\n\n{text}"}],
    )

    # Tool use guarantees structured output matching the schema
    return response.content[0].input
```

---

## Caching and Deduplication

```python
import hashlib
import json
from pathlib import Path

class LLMTransformCache:
    """Cache LLM transform results to avoid redundant API calls."""

    def __init__(self, cache_dir: str = ".llm_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.stats = {"hits": 0, "misses": 0}

    def _key(self, input_text: str, transform_type: str) -> str:
        content = f"{transform_type}:{input_text.strip()}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, input_text: str, transform_type: str) -> dict | None:
        key = self._key(input_text, transform_type)
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            self.stats["hits"] += 1
            return json.loads(path.read_text())
        self.stats["misses"] += 1
        return None

    def put(self, input_text: str, transform_type: str, result: dict):
        key = self._key(input_text, transform_type)
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps(result))

    @property
    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return self.stats["hits"] / total if total > 0 else 0

# Usage
cache = LLMTransformCache()

def cached_classify(record: dict) -> dict:
    cached = cache.get(record["text"], "classify")
    if cached:
        return cached

    result = classify_with_tools(record["text"])
    cache.put(record["text"], "classify", result)
    return result
```

---

## Data Quality Assessment

Use LLMs to assess data quality for text fields where traditional checks fall short:

```python
def assess_text_quality_batch(
    records: list[dict],
    text_field: str,
    batch_size: int = 30,
) -> list[dict]:
    """Assess quality of text fields using LLM judgment."""
    client = anthropic.Anthropic()
    results = []

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        items = "\n---\n".join(
            f"[{r['id']}] {r[text_field][:300]}" for r in batch
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system="""Assess each text for data quality. Return JSON array:
[{"id": "...", "quality_score": 1-5, "issues": ["truncated", "garbled", "wrong_language", "placeholder", "pii_detected"], "suggestion": "brief fix suggestion or null"}]
Only output JSON.""",
            messages=[{"role": "user", "content": items}],
        )

        results.extend(json.loads(response.content[0].text))

    return results
```

---

## Cost Monitoring

```python
import anthropic
from dataclasses import dataclass, field

@dataclass
class CostTracker:
    """Track LLM API costs for data pipeline runs."""
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0

    # Approximate pricing (Claude Haiku 4.5)
    INPUT_COST_PER_1M: float = 0.80
    OUTPUT_COST_PER_1M: float = 4.00

    @property
    def estimated_cost(self) -> float:
        return (
            (self.input_tokens / 1_000_000) * self.INPUT_COST_PER_1M
            + (self.output_tokens / 1_000_000) * self.OUTPUT_COST_PER_1M
        )

    def record(self, response):
        """Record usage from an API response."""
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        self.calls += 1

    def report(self) -> str:
        return (
            f"LLM Transform Cost Report:\n"
            f"  API calls: {self.calls}\n"
            f"  Input tokens: {self.input_tokens:,}\n"
            f"  Output tokens: {self.output_tokens:,}\n"
            f"  Estimated cost: ${self.estimated_cost:.4f}\n"
            f"  Cost per record: ${self.estimated_cost / max(self.calls, 1):.6f}"
        )

# Usage
tracker = CostTracker()

response = client.messages.create(...)
tracker.record(response)

print(tracker.report())
# LLM Transform Cost Report:
#   API calls: 40
#   Input tokens: 120,000
#   Output tokens: 30,000
#   Estimated cost: $0.2160
#   Cost per record: $0.005400
```

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| **Sending PII to LLM APIs** | Tier 2-3: Anonymize or mask PII before sending to LLM. Use local models for PII data. |
| **Data leakage via prompts** | Never include production data in system prompts. Use few-shot examples with synthetic data. |
| **LLM hallucination in transforms** | Always validate LLM output against expected schema (Pydantic). Log and review low-confidence results. |
| **Cost runaway** | Set per-pipeline cost budgets. Track costs per run. Alert when thresholds are exceeded. |
| **Non-determinism** | Cache results. Use `temperature=0` where supported. Log all inputs/outputs for audit. |
