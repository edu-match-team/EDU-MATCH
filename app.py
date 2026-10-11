import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  EduMatch Web Platform is running on http://127.0.0.1:5000")
    print("  Available Portals:")
    print("  - Homepage:       http://127.0.0.1:5000/")
    print("  - Student Login:  http://127.0.0.1:5000/student/login.html")
    print("  - Provider Login: http://127.0.0.1:5000/provider/login.html")
    print("  - Admin Login:    http://127.0.0.1:5000/admin/login.html")
    print("=" * 60 + "\n")
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
