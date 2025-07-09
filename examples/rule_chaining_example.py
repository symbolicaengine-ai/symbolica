#!/usr/bin/env python3
"""
Rule Chaining Example
====================

Demonstrates rule chaining capabilities where rules can trigger other rules
to create complex workflow scenarios.
"""

import json
from symbolica import Engine, facts

# Example 1: E-commerce Order Processing Workflow
order_processing_rules = """
rules:
  # Initial validation and classification
  - id: order_received
    priority: 100
    condition: "order_status == 'received'"
    actions:
      order_status: validated
      received_timestamp: "2024-01-01T10:00:00Z"
    triggers: [inventory_check, customer_validation]
    tags: [order, validation]
  
  # Parallel checks triggered by order validation
  - id: inventory_check
    priority: 80
    condition: "order_status == 'validated' and item_quantity <= stock_available"
    actions:
      inventory_reserved: true
      stock_available: 45  # Simulated stock reduction
    triggers: [payment_processing]
    tags: [inventory, logistics]
    
  - id: customer_validation
    priority: 80
    condition: "order_status == 'validated' and customer_tier in ['premium', 'vip']"
    actions:
      customer_validated: true
      priority_processing: true
    triggers: [loyalty_bonus]
    tags: [customer, validation]
  
  # Payment processing triggered by successful inventory check
  - id: payment_processing
    priority: 60
    condition: "inventory_reserved == true and payment_amount > 0"
    actions:
      payment_status: processed
      payment_id: "PAY_001"
    triggers: [shipping_preparation]
    tags: [payment, processing]
  
  # Loyalty bonus triggered by customer validation
  - id: loyalty_bonus
    priority: 60
    condition: "customer_validated == true and customer_tier == 'vip'"
    actions:
      loyalty_points: 100
      bonus_applied: true
    tags: [loyalty, bonus]
  
  # Shipping preparation triggered by payment
  - id: shipping_preparation
    priority: 40
    condition: "payment_status == 'processed'"
    actions:
      shipping_status: prepared
      tracking_number: "TRK_001"
    triggers: [notification_service]
    tags: [shipping, logistics]
  
  # Final notification triggered by shipping
  - id: notification_service
    priority: 20
    condition: "shipping_status == 'prepared'"
    actions:
      customer_notified: true
      email_sent: true
      order_status: completed
    tags: [notification, completion]
"""

def demo_order_processing_workflow():
    """Demonstrate complex order processing workflow with rule chaining."""
    print("=== E-commerce Order Processing Workflow ===")
    
    engine = Engine.from_yaml(order_processing_rules)
    
    # Test case: VIP customer order
    order_facts = facts(
        order_status="received",
        item_quantity=5,
        stock_available=50,
        customer_tier="vip",
        payment_amount=299.99
    )
    
    print(f"Initial order facts: {json.dumps(order_facts.data, indent=2)}")
    
    result = engine.reason(order_facts)
    
    print(f"\n=== Execution Results ===")
    print(f"Rules fired ({len(result.fired_rules)}): {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"\nFinal order state:")
    print(json.dumps(result.verdict, indent=2))
    
    print(f"\n=== Workflow Reasoning ===")
    print(result.reasoning)
    
    print(f"\n=== LLM-Friendly Context ===")
    llm_context = result.get_llm_context()
    print(json.dumps(llm_context, indent=2))


# Example 2: Risk Assessment and Fraud Detection
fraud_detection_rules = """
rules:
  # Initial transaction screening
  - id: transaction_received
    priority: 100
    condition: "transaction_amount > 0"
    actions:
      transaction_status: screening
      screening_timestamp: "2024-01-01T10:00:00Z"
    triggers: [amount_check, velocity_check, location_check]
    tags: [transaction, screening]
  
  # Amount-based risk assessment
  - id: amount_check
    priority: 80
    condition: "transaction_status == 'screening' and transaction_amount > 1000"
    actions:
      high_amount_flag: true
      risk_score: 30
    triggers: [enhanced_verification]
    tags: [risk, amount]
    
  # Velocity checking
  - id: velocity_check
    priority: 80
    condition: "transaction_status == 'screening' and transactions_24h > 5"
    actions:
      velocity_flag: true
      risk_score: 25
    triggers: [enhanced_verification]
    tags: [risk, velocity]
    
  # Location-based checking
  - id: location_check
    priority: 80
    condition: "transaction_status == 'screening' and location_country != home_country"
    actions:
      foreign_location_flag: true
      risk_score: 20
    triggers: [geo_verification]
    tags: [risk, location]
  
  # Enhanced verification for high-risk transactions
  - id: enhanced_verification
    priority: 60
    condition: "risk_score >= 25"
    actions:
      verification_required: true
      verification_level: enhanced
    triggers: [manual_review]
    tags: [verification, enhanced]
    
  # Geographic verification
  - id: geo_verification
    priority: 60
    condition: "foreign_location_flag == true"
    actions:
      geo_verification_required: true
      location_verified: false
    triggers: [location_notification]
    tags: [verification, geo]
  
  # Manual review for complex cases
  - id: manual_review
    priority: 40
    condition: "verification_required == true"
    actions:
      manual_review_queued: true
      transaction_status: pending_review
    tags: [review, manual]
    
  # Location-based notification
  - id: location_notification
    priority: 40
    condition: "geo_verification_required == true"
    actions:
      location_sms_sent: true
      customer_alerted: true
    tags: [notification, location]
"""

def demo_fraud_detection_workflow():
    """Demonstrate fraud detection workflow with multiple risk factors."""
    print("\n=== Fraud Detection Workflow ===")
    
    engine = Engine.from_yaml(fraud_detection_rules)
    
    # Test case: High-risk international transaction
    transaction_facts = facts(
        transaction_amount=2500,
        transactions_24h=7,
        location_country="FR",
        home_country="US",
        merchant_category="online"
    )
    
    print(f"Transaction facts: {json.dumps(transaction_facts.data, indent=2)}")
    
    result = engine.reason(transaction_facts)
    
    print(f"\n=== Risk Assessment Results ===")
    print(f"Rules fired ({len(result.fired_rules)}): {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"\nRisk assessment outcome:")
    print(json.dumps(result.verdict, indent=2))
    
    print(f"\n=== Risk Analysis Chain ===")
    print(result.reasoning)


# Example 3: Content Moderation Pipeline
content_moderation_rules = """
rules:
  # Initial content submission
  - id: content_submitted
    priority: 100
    condition: "content_type in ['post', 'comment', 'message']"
    actions:
      moderation_status: queued
      submission_time: "2024-01-01T10:00:00Z"
    triggers: [automated_scan, metadata_check]
    tags: [content, submission]
    
  # Automated content scanning
  - id: automated_scan
    priority: 80
    condition: "moderation_status == 'queued'"
    actions:
      scanned: true
      scan_score: 0.7
    triggers: [content_classification]
    tags: [automation, scanning]
    
  # Metadata and user reputation check
  - id: metadata_check
    priority: 80
    condition: "moderation_status == 'queued' and user_reputation < 50"
    actions:
      low_reputation_flag: true
      additional_checks_required: true
    triggers: [enhanced_review]
    tags: [metadata, reputation]
    
  # Content classification based on scan results
  - id: content_classification
    priority: 60
    condition: "scanned == true and scan_score > 0.5"
    actions:
      classification: suspicious
      confidence: 0.85
    triggers: [human_review]
    tags: [classification, ml]
    
  # Enhanced review for low reputation users
  - id: enhanced_review
    priority: 60
    condition: "additional_checks_required == true"
    actions:
      enhanced_scan: true
      review_priority: high
    triggers: [escalation]
    tags: [review, enhanced]
    
  # Human review for suspicious content
  - id: human_review
    priority: 40
    condition: "classification == 'suspicious'"
    actions:
      human_review_queued: true
      moderation_status: pending_human_review
    tags: [human, review]
    
  # Escalation for problematic cases
  - id: escalation
    priority: 40
    condition: "review_priority == 'high'"
    actions:
      escalated: true
      senior_moderator_assigned: true
    tags: [escalation, senior]
"""

def demo_content_moderation_pipeline():
    """Demonstrate content moderation pipeline with automated and human reviews."""
    print("\n=== Content Moderation Pipeline ===")
    
    engine = Engine.from_yaml(content_moderation_rules)
    
    # Test case: Suspicious content from low-reputation user
    content_facts = facts(
        content_type="post",
        user_reputation=25,
        content_length=500,
        contains_links=True
    )
    
    print(f"Content submission: {json.dumps(content_facts.data, indent=2)}")
    
    result = engine.reason(content_facts)
    
    print(f"\n=== Moderation Results ===")
    print(f"Rules fired ({len(result.fired_rules)}): {result.fired_rules}")
    print(f"Execution time: {result.execution_time_ms:.2f}ms")
    print(f"\nModeration outcome:")
    print(json.dumps(result.verdict, indent=2))
    
    print(f"\n=== Moderation Pipeline ===")
    print(result.reasoning)


def demo_chaining_analysis():
    """Analyze the rule chaining behavior."""
    print("\n=== Rule Chaining Analysis ===")
    
    # Use the order processing example for analysis
    engine = Engine.from_yaml(order_processing_rules)
    
    print(f"Total rules: {len(engine.rules)}")
    
    # Analyze trigger relationships
    print(f"\nRule Trigger Relationships:")
    for rule in engine.rules:
        if rule.triggers:
            print(f"  {rule.id} triggers: {rule.triggers}")
        else:
            print(f"  {rule.id} (no triggers)")
    
    # Show rule priorities and tags
    print(f"\nRule Details:")
    for rule in sorted(engine.rules, key=lambda r: r.priority, reverse=True):
        triggers_str = f" -> {rule.triggers}" if rule.triggers else ""
        tags_str = f" [{', '.join(rule.tags)}]" if rule.tags else ""
        print(f"  Priority {rule.priority}: {rule.id}{triggers_str}{tags_str}")


if __name__ == "__main__":
    print("Rule Chaining Examples")
    print("=" * 50)
    
    demo_order_processing_workflow()
    demo_fraud_detection_workflow()
    demo_content_moderation_pipeline()
    demo_chaining_analysis()
    
    print("\n" + "=" * 50)
    print("Rule Chaining Features Demonstrated:")
    print("✓ Sequential rule triggering")
    print("✓ Parallel rule execution")
    print("✓ Complex workflow orchestration")
    print("✓ Conditional chaining (triggered rules still need conditions)")
    print("✓ Integration with priorities and tags")
    print("✓ Clear reasoning with trigger relationships")
    print("✓ LLM-friendly workflow explanations") 