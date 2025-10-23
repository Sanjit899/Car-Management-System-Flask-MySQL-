🚗 Car Management System (Flask + MySQL)



A simple yet powerful Car Management System built using Python Flask, MySQL, and Bootstrap.
This project allows you to manage cars, customers, and rentals easily with a clean web interface.

⚙️ Features
Add, edit, and view Cars
Manage Customers
Track Rentals (with total cost calculation)
Responsive Bootstrap UI
MySQL Database Integration
Lightweight Flask backend

🗂️ Project Structure
car_management_system/
│
├── app.py
├── requirements.txt
├── README.md
├── static/
│   └── css/style.css
└── templates/
    ├── index.html
    ├── view_cars.html
    ├── add_car.html
    ├── edit_car.html
    ├── view_customers.html
    ├── add_customer.html
    ├── edit_customer.html
    ├── view_rentals.html
    ├── add_rental.html
    └── edit_rental.html


🧠 Tech Stack
Frontend: HTML, CSS, Bootstrap
Backend: Flask (Python)
Database: MySQL


⚡ How to Run Locally

Clone the Repository

git clone https://github.com/YOUR-USERNAME/car-management-system.git
cd car-management-system


Create a Virtual Environment

python -m venv venv
venv\Scripts\activate    # on Windows
source venv/bin/activate # on macOS/Linux


Install Dependencies

pip install -r requirements.txt


Setup MySQL Database

CREATE DATABASE car_rental;
USE car_rental;


Run the Application

python app.py


Open your browser and visit:
👉 http://127.0.0.1:5000/


📜 License

This project is open-source under the MIT License.
    
