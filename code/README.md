# EL Image Classification System

Solar Panel EL Image Classification System using Django for quality inspection and defect detection.

## Features

- User Authentication (Login)
- User Profile Management
- Role-based access control (Admin/User)
- Modern Dashboard Interface
- Image Upload System 
- AI-based Defect Detection

## Tech Stack

- **Backend:** Django 4.2
- **Database:** SQLite (Development) / PostgreSQL (Production)
- **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript
- **Authentication:** Django Authentication System
- **Icons:** Font Awesome 6

## Project Structure
code/
├── core/ # Main project configuration
├── apps/
| ├── users/ # User authentication app
| ├── inspections/ # Image inspection app
├── templates/ # HTML templates
│ ├── base_dashboard.html
│ ├── users/
│ └── inspections/
├── static/ # CSS, JS, images
│ ├── css/
│ └── js/
├── manage.py # Django management script
└── requirements.txt # Project dependencies

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/kavyaviki/EL-Image-Classification.git
   cd EL-Image-Classification/backend
   ```

2. **Create virtual environment**

   ```bash
    python -m venv venv
   ```
   Activate virtual environment

   Windows:

   ```bash
   venv\Scripts\activate
   ```
    Mac/Linux:

    ```bash
    source venv/bin/activate
    ```

3. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run migrations**

    ```bash
    python manage.py migrate
    ```

5. **Create superuser**

    ```bash
    python manage.py createsuperuser
    ```

6. **Run development server**

    ```bash
    python manage.py runserver
    ```

7. **Access the application**

*Main site*: http://127.0.0.1:8000/users/login/

*Admin panel*: http://127.0.0.1:8000/admin/