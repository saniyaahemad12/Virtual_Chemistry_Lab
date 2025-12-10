from app import app, db, User

with app.app_context():
    users = User.query.all()
    if not users:
        print("No users found in database!")
    else:
        for u in users:
            print(u.id, u.name, u.email, u.password, u.is_teacher)
