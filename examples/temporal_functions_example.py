#!/usr/bin/env python3
"""
Temporal Functions Example
===========================

Demonstrates temporal functions for:
- Infrastructure monitoring and alerting
- Session management with TTL
- Rate limiting and throttling
- SLA monitoring

Shows how custom functions + simple storage = powerful temporal capabilities!
"""

import time
from symbolica import Engine, facts

# Monitoring rules using temporal functions
monitoring_rules = """
rules:
  # Infrastructure monitoring
  - id: cpu_sustained_high
    priority: 100
    condition: "sustained_above('cpu_utilization', 90, 600)"  # > 90% for 10 minutes
    actions:
      alert: "CPU sustained high"
      severity: "critical"
      page_oncall: true
    tags: ["monitoring", "cpu"]
  
  - id: memory_trending_up
    priority: 90
    condition: "recent_avg('memory_usage', 300) > recent_avg('memory_usage', 1800)"  # 5min vs 30min
    actions:
      alert: "Memory usage trending upward"
      severity: "warning"
      investigate: true
    tags: ["monitoring", "memory"]
  
  - id: error_rate_spike
    priority: 95
    condition: "recent_avg('error_rate', 180) > 0.05"  # > 5% errors in last 3 minutes
    actions:
      alert: "Error rate spike detected"
      severity: "critical"
      rollback_candidate: true
    tags: ["monitoring", "errors"]
  
  # Session management
  - id: user_authenticated
    priority: 50
    condition: "has_ttl_fact(user_session_key)"
    actions:
      authenticated: true
      allow_access: true
    tags: ["auth", "session"]
  
  - id: session_expired
    priority: 60
    condition: "ttl_fact(user_session_key) == None and login_attempted == true"
    actions:
      authenticated: false
      redirect_to_login: true
      session_expired: true
    tags: ["auth", "session"]
  
  # Rate limiting
  - id: api_rate_limit
    priority: 80
    condition: "recent_count('api_calls', 60) >= 100"  # 100 calls per minute
    actions:
      rate_limited: true
      retry_after: 60
    tags: ["rate_limit", "api"]
  
  # SLA monitoring
  - id: sla_violation
    priority: 70
    condition: "recent_avg('response_time', 3600) > 2000"  # Avg response > 2s for 1 hour
    actions:
      sla_violated: true
      notify_management: true
      incident_id: "SLA-2024-001"
    tags: ["sla", "performance"]
  
  # Maintenance mode
  - id: maintenance_mode_active
    priority: 200
    condition: "ttl_fact('maintenance_mode') == true"
    actions:
      maintenance_active: true
      reject_requests: true
      maintenance_message: "System under maintenance"
    tags: ["maintenance"]
"""

def demo_infrastructure_monitoring():
    """Demonstrate infrastructure monitoring with temporal functions."""
    print("=== Infrastructure Monitoring Demo ===")
    
    engine = Engine.from_yaml(monitoring_rules)
    
    # Simulate CPU data over time
    print("Simulating CPU data points...")
    timestamps = []
    for i in range(15):  # 15 data points over simulated time
        cpu_value = 85 + (i * 2)  # Gradually increasing from 85% to 113%
        timestamp = time.time() - (600 - i * 40)  # Spread over 10 minutes
        engine.store_datapoint("cpu_utilization", cpu_value, timestamp)
        timestamps.append((timestamp, cpu_value))
        print(f"  t={i*40}s: CPU {cpu_value}%")
    
    # Test monitoring rules
    result = engine.reason(facts())
    print(f"\nMonitoring Result:")
    print(f"  Verdict: {result.verdict}")
    print(f"  Fired Rules: {result.fired_rules}")
    print(f"  Reasoning: {result.reasoning}")
    
    # Show temporal stats
    stats = engine.get_temporal_stats()
    print(f"\nTemporal Store Stats: {stats}")

def demo_session_management():
    """Demonstrate session management with TTL facts."""
    print("\n=== Session Management Demo ===")
    
    engine = Engine.from_yaml(monitoring_rules)
    
    user_id = "user_12345"
    session_key = f"session_{user_id}"
    
    # User logs in - set session with 30 minute TTL
    print("User logs in...")
    engine.set_ttl_fact(session_key, {"user_id": user_id, "login_time": time.time()}, 1800)
    
    # Check authentication immediately
    result1 = engine.reason(facts(user_session_key=session_key))
    print(f"Immediate auth check: {result1.verdict}")
    
    # Check authentication after some time (still valid)
    print("Checking auth after delay...")
    result2 = engine.reason(facts(user_session_key=session_key))
    print(f"Delayed auth check: {result2.verdict}")
    
    # Simulate session expiry for demo (set very short TTL)
    print("Setting short TTL to demo expiration...")
    engine.set_ttl_fact(session_key, {"user_id": user_id}, 1)  # 1 second TTL
    time.sleep(2)
    
    # Check after expiration
    result3 = engine.reason(facts(user_session_key=session_key, login_attempted=True))
    print(f"After expiration: {result3.verdict}")

def demo_rate_limiting():
    """Demonstrate rate limiting with time-based counting."""
    print("\n=== Rate Limiting Demo ===")
    
    engine = Engine.from_yaml(monitoring_rules)
    
    # Simulate API calls
    print("Simulating API calls...")
    for i in range(105):  # 105 calls - should trigger rate limit
        engine.store_datapoint("api_calls", 1)  # Each call is a data point
        if i % 20 == 0:
            print(f"  Made {i+1} API calls")
    
    # Check rate limiting
    result = engine.reason(facts())
    print(f"\nRate Limiting Result:")
    print(f"  Verdict: {result.verdict}")
    print(f"  Rate Limited: {'rate_limited' in result.verdict}")

def demo_sla_monitoring():
    """Demonstrate SLA monitoring with response time tracking."""
    print("\n=== SLA Monitoring Demo ===")
    
    engine = Engine.from_yaml(monitoring_rules)
    
    # Simulate response times over an hour (degrading performance)
    print("Simulating response time data over 1 hour...")
    
    # Good performance for first 30 minutes
    for i in range(30):
        response_time = 500 + (i * 10)  # 500ms to 800ms
        timestamp = time.time() - (3600 - i * 60)  # 1 hour ago to 30 min ago
        engine.store_datapoint("response_time", response_time, timestamp)
    
    # Degraded performance for last 30 minutes
    for i in range(30):
        response_time = 2500 + (i * 50)  # 2500ms to 4000ms (SLA violation)
        timestamp = time.time() - (1800 - i * 60)  # 30 min ago to now
        engine.store_datapoint("response_time", response_time, timestamp)
    
    # Check SLA
    result = engine.reason(facts())
    print(f"\nSLA Monitoring Result:")
    print(f"  Verdict: {result.verdict}")
    print(f"  SLA Violated: {'sla_violated' in result.verdict}")
    
    # Show temporal statistics
    recent_avg = engine._temporal_service._store.avg_in_window("response_time", 3600)
    print(f"  Average response time (1 hour): {recent_avg:.1f}ms")

def demo_maintenance_mode():
    """Demonstrate maintenance mode with TTL facts."""
    print("\n=== Maintenance Mode Demo ===")
    
    engine = Engine.from_yaml(monitoring_rules)
    
    # Regular operation
    result1 = engine.reason(facts())
    print(f"Normal operation: {result1.verdict}")
    
    # Enable maintenance mode for 2 hours
    print("Enabling maintenance mode for 2 hours...")
    engine.set_ttl_fact("maintenance_mode", True, 7200)  # 2 hours
    
    result2 = engine.reason(facts())
    print(f"Maintenance mode active: {result2.verdict}")
    
    # Check if maintenance is active
    maintenance_active = engine._temporal_service._store.get_ttl_fact("maintenance_mode")
    print(f"Maintenance mode fact: {maintenance_active}")

def demo_complex_scenario():
    """Demonstrate complex scenario combining multiple temporal functions."""
    print("\n=== Complex Scenario: System Under Load ===")
    
    engine = Engine.from_yaml(monitoring_rules)
    
    # Simulate a system under increasing load
    print("Simulating system under increasing load...")
    
    # Start with normal metrics
    for i in range(10):
        timestamp = time.time() - (600 - i * 60)  # Last 10 minutes
        
        # CPU gradually increases
        cpu = 70 + (i * 3)
        engine.store_datapoint("cpu_utilization", cpu, timestamp)
        
        # Memory usage increases
        memory = 60 + (i * 4)
        engine.store_datapoint("memory_usage", memory, timestamp)
        
        # Error rate spikes in last few minutes
        error_rate = 0.01 if i < 7 else 0.08  # Normal then spike
        engine.store_datapoint("error_rate", error_rate, timestamp)
        
        print(f"  t={i}min: CPU {cpu}%, Memory {memory}%, Errors {error_rate*100:.1f}%")
    
    # Evaluate all rules
    result = engine.reason(facts())
    
    print(f"\nSystem Health Assessment:")
    print(f"  Alerts Triggered: {len(result.fired_rules)}")
    print(f"  Fired Rules: {result.fired_rules}")
    print(f"  Actions: {result.verdict}")
    print(f"\nDetailed Reasoning:")
    print(f"  {result.reasoning}")

def show_available_temporal_functions():
    """Show all available temporal functions."""
    print("\n=== Available Temporal Functions ===")
    
    engine = Engine()
    functions = engine.list_functions()
    
    temporal_functions = {name: desc for name, desc in functions.items() 
                         if any(keyword in name for keyword in ['recent', 'sustained', 'ttl'])}
    
    print("Temporal functions available in rules:")
    for name, desc in temporal_functions.items():
        print(f"  {name}: {desc}")
    
    print("\nExample usage in YAML rules:")
    print("""
  - id: example_rule
    condition: "recent_avg('cpu_util', 300) > 80"
    actions:
      high_cpu: true
      
  - id: sustained_condition
    condition: "sustained_above('memory_usage', 90, 600)"
    actions:
      memory_alert: true
      
  - id: session_check
    condition: "has_ttl_fact('user_session')"
    actions:
      authenticated: true
    """)

if __name__ == "__main__":
    show_available_temporal_functions()
    demo_infrastructure_monitoring()
    demo_session_management()
    demo_rate_limiting()
    demo_sla_monitoring()
    demo_maintenance_mode()
    demo_complex_scenario()
    
    print("\n=== Temporal Functions Demo Complete ===")
    print("✓ Time-series monitoring and alerting")
    print("✓ Session management with TTL")
    print("✓ Rate limiting with time windows")
    print("✓ SLA monitoring with averages")
    print("✓ Maintenance mode with expiration")
    print("✓ Complex multi-metric scenarios")
    print("\n🚀 Production-ready temporal capabilities via custom functions!") 