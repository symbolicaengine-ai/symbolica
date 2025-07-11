# Custom Functions Example

This example demonstrates how to extend Symbolica with custom business logic using **lambda functions**.

## Key Concept

**Lambda functions** are the recommended way to add custom logic to Symbolica:
- **Safe by default** - No side effects or security risks
- **Simple syntax** - Easy to define inline business logic  
- **No special flags** - Registers automatically without `allow_unsafe=True`
- **Fast execution** - Efficient evaluation within rule conditions

## Running the Example

```bash
cd examples/02_custom_functions
python example.py
```

## Lambda Functions Demonstrated

### Risk Score Function
```python
engine.register_function("risk_score", 
    lambda credit, income, debt: (
        "low" if credit >= 700 and income >= 60000 and debt <= 0.3 else
        "medium" if credit >= 600 and income >= 40000 and debt <= 0.5 else
        "high"
    )
)
```

### Fraud Detection Function
```python
engine.register_function("fraud_check",
    lambda amount, avg_tx: amount > avg_tx * 4 or amount > 200000
)
```

## Rules Using Lambda Functions

```yaml
rules:
  - id: low_risk_loan
    condition: "risk_score(credit_score, income, debt_ratio) == 'low'"
    actions:
      approved: true
      interest_rate: 0.05
      loan_type: "prime"
  
  - id: fraud_detection
    condition: "fraud_check(loan_amount, avg_transaction) == True"
    actions:
      approved: false
      flagged_for_review: true
      reason: "Potential fraud detected"
```

## Sample Output

```
Custom Functions Example
==================================================
Registering lambda functions (safe by default):
  ✓ risk_score: lambda function for credit risk assessment
  ✓ fraud_check: lambda function for fraud detection

Test 1: Low Risk Customer
Input: Credit 780, Income $80,000, Debt ratio 0.2
Result: {'approved': True, 'interest_rate': 0.05, 'loan_type': 'prime'}

Lambda Function Benefits:
  ✓ Safe by default - no side effects
  ✓ Simple syntax - easy to understand  
  ✓ No allow_unsafe=True required
  ✓ Fast execution within rule conditions
```

## Benefits of Lambda Functions

1. **Safety**: No risk of hanging the engine or memory issues
2. **Simplicity**: Business logic defined in one clear expression
3. **Performance**: Fast execution during rule evaluation
4. **No Special Setup**: Registers without safety flags

This approach lets you extend Symbolica's capabilities safely and efficiently. 