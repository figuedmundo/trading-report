# Conservative Trading Analysis Prompt

Analyze the following trading report conservatively, focusing only on high-confidence opportunities:

## Summary
Summary (100-150 words) of only the most significant findings and clear recommendations.

## Market Analysis
Key market observations and trends that are clearly stated or strongly implied in the report.

## Trading Operations
ONLY include trading operations that are explicitly mentioned or strongly recommended with high confidence.
Provide as JSON array with:
- action, symbol, entry_price, target_price, stop_loss, timeframe, confidence_score
Confidence must be >= 0.75 to include. If uncertain or no clear signals found, omit this section entirely.

## Risk Assessment
Primary risks and clear mitigation strategies.

## Additional Insights
Minimal - only include if critically important.

REPORT CONTENT:
{content}

Return ONLY the analysis with markdown sections. Be conservative - omit uncertain information.
