# Teachers' Timetable Generator using AI

This project is a Flask-based web application designed to automate the creation and management of teachers' timetables using AI-driven scheduling techniques. It enables Heads of Departments (HODs) to generate optimized timetables, manage teacher leave requests, and assign substitutes efficiently, while providing teachers with an interface to view their schedules and request leaves.

## Features

- **User Authentication**: Supports distinct roles for HODs and Teachers with secure login, registration, and password management.
- **Timetable Generation**: AI-powered scheduling with constraints to limit consecutive busy sessions (max 4) and ensure at least one free session per day.
- **Leave Management**: Teachers can request leaves, with automatic substitute assignment based on availability.
- **Department Management**: HODs can add, remove, and manage teachers within their department, including resetting passwords.
- **Calendar Integration**: Displays timetables and leave events in a visual calendar format.
- **Email Notifications**: Sends automated emails for leave requests, substitute assignments, and password resets.

## Technologies Used

- **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Mail
- **Database**: SQLite (configurable for other SQLAlchemy-supported databases)
- **Frontend**: HTML, CSS, JavaScript (with Jinja2 templating)
- **AI Logic**: Custom constraint-based scheduling algorithm
- **Dependencies**: Includes matplotlib (though usage is not evident in core files; possibly for future visualization)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/manishk050/Teachers-Timetable-Generator-using-AI.git
   cd Teachers-Timetable-Generator-using-AI
   ```

2. **Create a Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   - Create a `.env` file in the root directory (optional, as configs are currently hardcoded in `flask_app.py`):
     ```
     FLASK_APP=flask_app.py
     FLASK_ENV=development
     SECRET_KEY=your_secret_key_here
     MAIL_USERNAME=your_email@gmail.com
     MAIL_PASSWORD=your_email_password
     SQLALCHEMY_DATABASE_URI=sqlite:///instance/timetable.db
     ```
   - Replace placeholders with your own values. For security, update `flask_app.py` to load these from the `.env` file using a library like `python-dotenv`.

5. **Initialize the Database**:
   - The SQLite database (`timetable.db`) is automatically created in the `instance/` folder on first run.

## Usage

1. **Run the Application**:
   ```bash
   flask run
   ```
   - Or use `python flask_app.py` for debug mode.

2. **Access the Application**:
   - Navigate to `http://127.0.0.1:5000/` in your browser.

3. **Register as HOD**:
   - Visit `/register`, provide username, email, password, and department to sign up as an HOD.

4. **Add Teachers**:
   - Log in as HOD, go to `/add_teacher`, and input teacher details (username, email, password).

5. **Create Timetables**:
   - Use `/create_timetable/<teacher_id>` to generate and edit a teacher’s weekly timetable, specifying days and sessions.

6. **View Dashboard**:
   - Access `/dashboard` to see a calendar of timetables and leave events. Teachers can apply for leaves here.

7. **Manage Leave Requests**:
   - HODs can view department leave requests at `/report`.

## Project Structure

- **`flask_app.py`**: Core application file defining routes and configurations.
- **`timetable_logic.py`**: Implements timetable generation and substitute assignment logic.
- **`models.py`**: Defines database models (User, Timetable, LeaveRequest).
- **`database.py`**: Initializes SQLAlchemy database instance.
- **`utils.py`**: Provides utility functions for password reset tokens.
- **`templates/`**: Contains HTML templates for the frontend.
- **`instance/`**: Stores the SQLite database file (`timetable.db`).

## Notes

- **Matplotlib**: Listed in `requirements.txt` but not used in provided code. Remove it if unnecessary or document its intended use (e.g., timetable visualization).
- **Security**: Sensitive data (e.g., `SECRET_KEY`, email credentials) is hardcoded in `flask_app.py`. Consider using environment variables for production.
- **Scalability**: Currently uses SQLite; for larger deployments, configure a more robust database via `SQLALCHEMY_DATABASE_URI`.

## Contributing

Contributions are welcome! Fork the repository, make your changes, and submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or feedback, reach out to [manishk050](https://github.com/manishk050).