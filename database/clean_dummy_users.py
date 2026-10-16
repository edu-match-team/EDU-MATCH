import sqlite3

def clean_database():
    conn = sqlite3.connect('database/edumatch.db')
    cur = conn.cursor()

    # Find dummy accounts (keeping admin and the user's fresh test account ARYAN)
    cur.execute("SELECT id, full_name, email, role FROM users WHERE role != 'admin' AND LOWER(email) != 'ar@gmail.com'")
    dummy_users = cur.fetchall()
    print(f"Found {len(dummy_users)} dummy users to remove.")

    dummy_ids = [u[0] for u in dummy_users]
    if dummy_ids:
        placeholders = ','.join('?' for _ in dummy_ids)
        
        cur.execute(f"DELETE FROM student_profiles WHERE user_id IN ({placeholders})", dummy_ids)
        cur.execute(f"DELETE FROM provider_skills WHERE provider_id IN (SELECT id FROM provider_profiles WHERE user_id IN ({placeholders}))", dummy_ids)
        cur.execute(f"DELETE FROM portfolio_projects WHERE provider_id IN (SELECT id FROM provider_profiles WHERE user_id IN ({placeholders}))", dummy_ids)
        cur.execute(f"DELETE FROM services WHERE provider_id IN (SELECT id FROM provider_profiles WHERE user_id IN ({placeholders}))", dummy_ids)
        cur.execute(f"DELETE FROM certifications WHERE provider_id IN (SELECT id FROM provider_profiles WHERE user_id IN ({placeholders}))", dummy_ids)
        cur.execute(f"DELETE FROM provider_profiles WHERE user_id IN ({placeholders})", dummy_ids)
        cur.execute(f"DELETE FROM requirements WHERE student_id IN ({placeholders})", dummy_ids)
        cur.execute(f"DELETE FROM collaboration_requests WHERE student_id IN ({placeholders}) OR provider_id IN ({placeholders})", dummy_ids + dummy_ids)
        cur.execute(f"DELETE FROM messages WHERE sender_id IN ({placeholders}) OR conversation_id IN (SELECT id FROM conversations WHERE user1_id IN ({placeholders}) OR user2_id IN ({placeholders}))", dummy_ids + dummy_ids + dummy_ids)
        cur.execute(f"DELETE FROM conversations WHERE user1_id IN ({placeholders}) OR user2_id IN ({placeholders})", dummy_ids + dummy_ids)
        cur.execute(f"DELETE FROM reviews WHERE student_id IN ({placeholders}) OR provider_id IN ({placeholders})", dummy_ids + dummy_ids)
        cur.execute(f"DELETE FROM notifications WHERE user_id IN ({placeholders})", dummy_ids)
        cur.execute(f"DELETE FROM users WHERE id IN ({placeholders})", dummy_ids)
        conn.commit()

    print("Database cleanup complete! Remaining accounts in database:")
    cur.execute("SELECT id, full_name, email, role FROM users")
    for r in cur.fetchall():
        print(r)

if __name__ == '__main__':
    clean_database()
