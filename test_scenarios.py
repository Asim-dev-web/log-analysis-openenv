from server.scenarios import ALL_SCENARIOS, SCENARIOS_BY_DIFFICULTY, ALL_ROOT_CAUSES, ALL_RECOMMENDED_ACTIONS

print(f"Total: {len(ALL_SCENARIOS)}")
print(f"Easy: {len(SCENARIOS_BY_DIFFICULTY['easy'])}")
print(f"Medium: {len(SCENARIOS_BY_DIFFICULTY['medium'])}")
print(f"Hard: {len(SCENARIOS_BY_DIFFICULTY['hard'])}")

print("\n=== Validating Scenarios ===")
errors = []

for scenario in ALL_SCENARIOS:
    sid = scenario['id']
    
    # Check root cause exists in our list
    rc = scenario['ground_truth']['root_cause']
    if rc not in ALL_ROOT_CAUSES:
        errors.append(f"{sid}: root_cause '{rc}' not in ALL_ROOT_CAUSES")
    
    # Check recommended action exists
    action = scenario['ground_truth']['recommended_action']
    if action not in ALL_RECOMMENDED_ACTIONS:
        errors.append(f"{sid}: action '{action}' not in ALL_RECOMMENDED_ACTIONS")

if errors:
    print("ERRORS FOUND:")
    for e in errors:
        print(f"  - {e}")
else:
    print("All scenarios valid!")