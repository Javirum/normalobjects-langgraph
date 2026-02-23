import json
from dotenv import load_dotenv
load_dotenv()

from main import run_complaint, visualize_workflow_path

test_complaints = [
    "The Downside Up portal opens at different times each day. How do I predict when?",
    "Demogorgons sometimes work together and sometimes fight. What's their deal?",
    "El can move things with her mind but can't lift heavy rocks. Why?",
    "Why do creatures and power lines react so strangely together?",
    "This is not a valid complaint about something random",
]

results = []
for i, complaint in enumerate(test_complaints, 1):
    print(f"\n[{i}/{len(test_complaints)}] Processing: {complaint[:60]}...")
    state = run_complaint(complaint)
    result = {k: v for k, v in state.items() if k != "context"}
    results.append(result)
    print(visualize_workflow_path(state))

with open("results.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\nDone! Results saved to results.json")
