import sys
import requests

BASE_URL = "http://127.0.0.1:8000/api"

print("--- GRIDLOCK 2.0 SHIFT SIMULATION TEST ---")
score = 0
total_steps = 14

def print_result(step_num, title, passed, details=""):
    global score
    status = "PASS" if passed else "FAIL"
    if passed:
        score += 1
    print(f"Step {step_num}: {title} -> {status}")
    if details:
        print(f"   {details}")

# Step 1: Login as cr_central
cr_token = None
try:
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": "cr_central@blrtraffic.gov.in", "password": "central123"})
    if res.status_code == 200:
        cr_token = res.json().get("access_token")
        print_result(1, "Login as cr_central", True, f"Token: {cr_token[:15]}...")
    else:
        print_result(1, "Login as cr_central", False, res.text)
        sys.exit(1)
except Exception as e:
    print_result(1, "Login as cr_central", False, str(e))
    sys.exit(1)

headers = {"Authorization": f"Bearer {cr_token}"}

# Step 2: GET /dashboard/stats
try:
    res = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)
    if res.status_code == 200 and "total_red_zones" in res.json():
        print_result(2, "GET /dashboard/stats", True, f"Red Zones: {res.json().get('total_red_zones')}")
    else:
        print_result(2, "GET /dashboard/stats", False, res.text)
except Exception as e:
    print_result(2, "GET /dashboard/stats", False, str(e))

# Step 3: GET /zones?tier=red
try:
    res = requests.get(f"{BASE_URL}/zones/", headers=headers, params={"tier": "red"})
    if res.status_code == 200:
        red_zones_count = len(res.json())
        print_result(3, "GET /zones?tier=red", True, f"Returned {red_zones_count} zones")
    else:
        print_result(3, "GET /zones?tier=red", False, res.text)
except Exception as e:
    print_result(3, "GET /zones?tier=red", False, str(e))

# Step 4: GET /zones/unassigned-red
top_zone_id = None
try:
    res = requests.get(f"{BASE_URL}/zones/unassigned-red", headers=headers)
    if res.status_code == 200 and len(res.json()) > 0:
        top_zone = res.json()[0]
        top_zone_id = top_zone.get("zone_id")
        print_result(4, "GET /zones/unassigned-red", True, f"Top zone: {top_zone_id}")
    else:
        print_result(4, "GET /zones/unassigned-red", False, "No unassigned red zones found")
except Exception as e:
    print_result(4, "GET /zones/unassigned-red", False, str(e))

# Step 5: GET /teams?status=available
top_team_id = None
try:
    res = requests.get(f"{BASE_URL}/teams/", headers=headers, params={"status": "available"})
    if res.status_code == 200 and len(res.json()) > 0:
        top_team = res.json()[0]
        top_team_id = top_team.get("team_id")
        print_result(5, "GET /teams?status=available", True, f"Available team: {top_team_id}")
    else:
        print_result(5, "GET /teams?status=available", False, "No available teams found")
except Exception as e:
    print_result(5, "GET /teams?status=available", False, str(e))

# Step 6: POST /assignments/create
assignment_id = None
try:
    if top_zone_id and top_team_id:
        payload = {"zone_id": top_zone_id, "team_id": top_team_id}
        res = requests.post(f"{BASE_URL}/assignments/create", headers=headers, json=payload)
        if res.status_code == 200:
            assignment_id = res.json().get("assignment_id")
            print_result(6, "POST /assignments/create", True, f"Created Assignment: {assignment_id}")
        else:
            print_result(6, "POST /assignments/create", False, res.text)
    else:
        print_result(6, "POST /assignments/create", False, "Skipped due to missing zone/team")
except Exception as e:
    print_result(6, "POST /assignments/create", False, str(e))

# Step 7: Login as that team's officer
cop_token = None
cop_headers = {}
try:
    if top_team_id:
        cop_email = f"officer_{top_team_id.lower()}@blrtraffic.gov.in"
        team_num = top_team_id.replace("T", "")
        res = requests.post(f"{BASE_URL}/auth/login", data={"username": cop_email, "password": f"cop{team_num}"})
        if res.status_code == 200:
            cop_token = res.json().get("access_token")
            cop_headers = {"Authorization": f"Bearer {cop_token}"}
            print_result(7, f"Login as officer ({cop_email})", True)
        else:
            print_result(7, "Login as officer", False, res.text)
    else:
        print_result(7, "Login as officer", False, "Skipped due to missing team")
except Exception as e:
    print_result(7, "Login as officer", False, str(e))

# Step 8: POST /assignments/{id}/status-update -> enroute
try:
    if assignment_id and cop_token:
        payload = {"new_status": "enroute", "notes": "On my way"}
        res = requests.post(f"{BASE_URL}/assignments/{assignment_id}/status-update", headers=cop_headers, json=payload)
        if res.status_code == 200:
            print_result(8, "Update status -> enroute", True)
        else:
            print_result(8, "Update status -> enroute", False, res.text)
    else:
        print_result(8, "Update status -> enroute", False, "Skipped")
except Exception as e:
    print_result(8, "Update status -> enroute", False, str(e))

# Step 9: POST /assignments/{id}/status-update -> onsite
try:
    if assignment_id and cop_token:
        payload = {"new_status": "onsite", "notes": "Arrived at location"}
        res = requests.post(f"{BASE_URL}/assignments/{assignment_id}/status-update", headers=cop_headers, json=payload)
        if res.status_code == 200:
            print_result(9, "Update status -> onsite", True)
        else:
            print_result(9, "Update status -> onsite", False, res.text)
    else:
        print_result(9, "Update status -> onsite", False, "Skipped")
except Exception as e:
    print_result(9, "Update status -> onsite", False, str(e))

# Step 10: POST /feedback/submit
try:
    if assignment_id and cop_token:
        payload = {
            "assignment_id": assignment_id,
            "actual_violations_found": 15,
            "outcome_type": "resolved_quickly",
            "notes": "Situation resolved"
        }
        res = requests.post(f"{BASE_URL}/feedback/submit", headers=cop_headers, json=payload)
        if res.status_code == 200:
            print_result(10, "Submit feedback", True)
        else:
            print_result(10, "Submit feedback", False, res.text)
    else:
        print_result(10, "Submit feedback", False, "Skipped")
except Exception as e:
    print_result(10, "Submit feedback", False, str(e))

# Step 11: GET /dashboard/team-availability-forecast
try:
    res = requests.get(f"{BASE_URL}/dashboard/team-availability-forecast", headers=headers)
    if res.status_code == 200:
        forecasts = res.json()
        print_result(11, "GET team-availability-forecast", True, f"Returned {len(forecasts)} forecasts")
    else:
        print_result(11, "GET team-availability-forecast", False, res.text)
except Exception as e:
    print_result(11, "GET team-availability-forecast", False, str(e))

# Step 12: POST /chatbot/query
try:
    payload = {"question": "Which zones need urgent attention?"}
    res = requests.post(f"{BASE_URL}/chatbot/query", headers=headers, json=payload)
    if res.status_code == 200:
        print_result(12, "Chatbot Query", True, res.json().get("answer", "")[:50] + "...")
    else:
        print_result(12, "Chatbot Query", False, res.text)
except Exception as e:
    print_result(12, "Chatbot Query", False, str(e))

# Step 13: Login as superadmin -> GET /zones
sa_headers = {}
try:
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": "superadmin@blrtraffic.gov.in", "password": "admin123"})
    if res.status_code == 200:
        sa_token = res.json().get("access_token")
        sa_headers = {"Authorization": f"Bearer {sa_token}"}
        z_res = requests.get(f"{BASE_URL}/zones/", headers=sa_headers)
        if z_res.status_code == 200:
            print_result(13, "Superadmin GET /zones", True, f"Found {len(z_res.json())} total zones across regions")
        else:
            print_result(13, "Superadmin GET /zones", False, z_res.text)
    else:
        print_result(13, "Superadmin GET /zones", False, "Login failed")
except Exception as e:
    print_result(13, "Superadmin GET /zones", False, str(e))

# Step 14: POST /teams/add
try:
    payload = {
        "team_id": "T042",
        "station": "Cubbon Park PS",
        "region": "Central",
        "category": "QRT",
        "size": 4,
        "officer_names": ["Rajesh K", "Suresh M"],
        "vehicle_type": "Interceptor"
    }
    res = requests.post(f"{BASE_URL}/teams/add", headers=sa_headers, json=payload)
    if res.status_code == 200:
        print_result(14, "POST /teams/add (T042)", True)
    else:
        print_result(14, "POST /teams/add (T042)", False, res.text)
except Exception as e:
    print_result(14, "POST /teams/add (T042)", False, str(e))

print(f"\nOverall Score: {score}/{total_steps} Passed")
