# 📝 Evaluation & Feedback Report: [Feature / Macro Name]

> **Author**: [@username](https://github.com/username)  
> **Date**: YYYY-MM-DD  
> **Confluence Environment**: Cloud / Server / Data Center  
> **Target Document / Macro**: e.g., Draw.io, Lucidchart, Custom Nested Matrix, Multi-Tier Comments  

---

## 1. Executive Summary

Provide a concise overview of the document conversion scenario, the specific element/macro that experienced degradation or parsing issues, and the impact on the final `prd.md` document.

---

## 2. Input Sample (HTML / Storage XML Snippet)

Provide a sanitized snippet of the raw Confluence Storage XML or View HTML representation:

```xml
<!-- Sanitized sample snippet -->
<ac:structured-macro ac:name="custom-macro">
    <ac:parameter ac:name="title">Architecture Diagram</ac:parameter>
    <ac:rich-text-body>
        <p>Custom macro body...</p>
    </ac:rich-text-body>
</ac:structured-macro>
```

---

## 3. Current Converter Output vs Expected Ideal Output

### ❌ Current Output
```markdown
[Broken or missing markdown output]
```

### ✅ Expected Ideal Output
```markdown
[Clean, zero-loss markdown representation]
```

---

## 4. Proposed Solution & Implementation Notes

- **Target Component**: `core/parser.py`, `core/formatters.py`, `core/clean.py`, or `core/confluence_client.py`
- **Recommended Transformation Logic**:
  Explain how the AST or DOM node should be parsed and mapped.

---

## 5. Verification & Test Case Suggestion

Describe the unit test assertion to add to `tests/test_converter.py` to prevent future regressions.
