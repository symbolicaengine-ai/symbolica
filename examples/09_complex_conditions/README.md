# Complex Logical Conditions

This example demonstrates Symbolica's powerful structured condition syntax using **ANY**, **ALL**, and **NOT** operators to build sophisticated business logic for real-world scenarios.

## What This Example Shows

### Core Concepts
- **Nested logical structures** - Combine ANY, ALL, NOT in sophisticated ways
- **Complex eligibility workflows** - Insurance underwriting with multiple factors
- **Real-world business logic** - Accurate modeling of decision processes
- **Readable condition syntax** - More maintainable than complex boolean expressions

### Logical Operators

#### ALL Operator
All conditions must be true:
```yaml
condition:
  all:
    - "age >= 25"
    - "driving_experience_years >= 5"
    - "credit_score >= 700"
```

#### ANY Operator  
At least one condition must be true:
```yaml
condition:
  any:
    - "credit_score >= 750"
    - "previous_insurance == True" 
    - "education == 'college_graduate'"
```

#### NOT Operator
Excludes specific scenarios:
```yaml
condition:
  not:
    any:
      - "accidents_last_3_years >= 2"
      - "tickets_last_3_years >= 3"
```

## Running the Example

```bash
cd examples/09_complex_conditions
python example.py
```

## Sample Output

```
Symbolica Complex Conditions Example
=============================================
Loaded 11 underwriting rules

==================================================
Test Case 1: Young driver with excellent record
==================================================

Young Excellent Driver Results:
  Status: approved
  Premium Tier: young_driver
  Risk Level: medium_high
  Base Premium: $2,400
  Total Premium: $2,280
  Discounts Applied: good_student, young_professional
  Special Conditions: defensive_driving_course_recommended
  Execution Time: 0.85ms
  Rules Fired: 4

  Reasoning:
    ✓ young_driver_special: Complex nested condition satisfied
    ✓ multi_factor_discount: Multiple low-risk factors present
    ✓ credit_score_impact: Good credit score applied
    ✓ final_premium_calculation: Total premium calculated
```

## Complex Condition Examples

### 1. Premium Customer Qualification
**Business Logic**: Must meet age/experience requirements AND have good credit OR insurance history AND NOT have poor driving record.

```yaml
condition:
  all:
    - "age >= 25"
    - "driving_experience_years >= 5"
    - any:
        - "credit_score >= 700"
        - all:
            - "credit_score >= 650"
            - "previous_insurance == True"
            - "coverage_lapse_months <= 6"
    - not:
        any:
          - "accidents_last_3_years >= 2"
          - "tickets_last_3_years >= 3"
```

### 2. Young Driver Special Consideration
**Business Logic**: Young drivers can qualify if they have excellent record with good education/profession OR decent record with excellent credit and insurance history, BUT NOT if they have high-risk vehicles.

```yaml
condition:
  all:
    - "age < 25"
    - "driving_experience_years >= 2"
    - any:
        - all:
            - "accidents_last_3_years == 0"
            - "tickets_last_3_years == 0"
            - any:
                - "education == 'college_graduate'"
                - "occupation == 'engineer'"
                - "occupation == 'teacher'"
        - all:
            - "accidents_last_3_years <= 1"
            - "tickets_last_3_years <= 1"
            - "credit_score >= 720"
            - "previous_insurance == True"
    - not:
        any:
          - "vehicle_type == 'sports_car'"
          - "vehicle_type == 'motorcycle'"
          - "annual_mileage > 20000"
```

### 3. High-Risk Denial Conditions
**Business Logic**: Deny coverage for multiple high-risk scenarios UNLESS they're qualified commercial drivers.

```yaml
condition:
  any:
    - all:
        - "age < 21"
        - any:
            - "accidents_last_3_years >= 2"
            - "tickets_last_3_years >= 4"
            - "vehicle_type == 'sports_car'"
    - all:
        - "accidents_last_3_years >= 3"
        - any:
            - "tickets_last_3_years >= 3"
            - "credit_score < 500"
    - not:
        all:
          - "commercial_license == True"
          - "vehicle_type == 'commercial_truck'"
          - "years_commercial_driving >= 5"
```

## Key Features Demonstrated

### 1. **Nested Logic Structures**
- Multiple levels of ANY/ALL/NOT nesting
- Complex decision trees that mirror real business logic
- Readable and maintainable condition syntax

### 2. **Business Rule Accuracy**
- Insurance underwriting reflects real-world complexity
- Multiple risk factors considered simultaneously
- Graduated responses based on risk profiles

### 3. **Condition Combinations**
- Mix simple comparisons with complex nested logic
- Combine multiple risk factors intelligently
- Handle edge cases and exceptions properly

### 4. **Maintainable Logic**
- Easy to understand business requirements
- Simple to modify individual conditions
- Clear reasoning output for debugging

## Real-World Applications

### Insurance Underwriting
- Risk assessment with multiple factors
- Graduated pricing based on combined risk
- Exclusion rules for high-risk scenarios

### Loan Approval
- Credit worthiness with multiple criteria
- Income verification with fallback options
- Risk mitigation requirements

### Customer Qualification
- Tiered service levels based on multiple factors
- Discount eligibility with complex rules
- Special consideration workflows

### Compliance Checking
- Regulatory requirements with multiple paths
- Exception handling for special cases
- Audit trail for decision rationale

## Benefits Over Simple Boolean Logic

### 1. **Readability**
```yaml
# Complex boolean (hard to read)
condition: "(age >= 25 && exp >= 5) && (credit >= 700 || (credit >= 650 && insurance && lapse <= 6)) && !(accidents >= 2 || tickets >= 3)"

# Structured conditions (easy to read)
condition:
  all:
    - "age >= 25"
    - "driving_experience_years >= 5"
    - any:
        - "credit_score >= 700"
        - all:
            - "credit_score >= 650"
            - "previous_insurance == True"
            - "coverage_lapse_months <= 6"
    - not:
        any:
          - "accidents_last_3_years >= 2"
          - "tickets_last_3_years >= 3"
```

### 2. **Maintainability**
- Add/remove conditions without complex parentheses
- Modify individual criteria independently
- Clear structure for business analysts

### 3. **Error Handling** 
- Better error messages for failed conditions
- Easier debugging with structured output
- Clear reasoning about which parts failed

### 4. **Business Alignment**
- Matches how business analysts think
- Easy to translate requirements to rules
- Natural way to express complex policies

## Extending the Example

### Add New Risk Factors
```yaml
- id: "environmental_risk_factor"
  condition:
    all:
      - any:
          - "location == 'hurricane_zone'"
          - "location == 'flood_zone'"
          - "location == 'earthquake_zone'"
      - not:
          all:
            - "vehicle_garaged == True"
            - "comprehensive_coverage == True"
```

### Combine with LLM Intelligence
```yaml
- id: "ai_enhanced_risk_assessment"
  condition:
    all:
      - "PROMPT('Analyze risk profile: {customer_data}', 'int') <= 7"
      - any:
          - "traditional_risk_score <= 'medium'"
          - "PROMPT('Any mitigating factors: {history}', 'bool') == true"
```

This example shows how Symbolica's structured conditions enable sophisticated business logic that's both powerful and maintainable, making it perfect for complex decision-making scenarios in production systems. 