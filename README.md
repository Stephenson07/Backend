# Installation
## 1. Prerequisites

- Git 
- Python 3.8+
- pip

## 2. Clone the Repository

```
git clone https://github.com/Stephenson07/Backend
```


## 3. Navigate to project directory
```
cd your-flask-repo

# Create the Virtual Environment

python -m venv ./
```

- Activate the virtual environment
```
.Scripts\Activate.ps1
```
- Install the requirments
```
pip install -r requirements.txt
```
- create a .env file with the keys in .env.example

## 4. Get your gemini API 
- Log into AI Studio: Go to AI Studio and log in with your Google account.

- Create a new project or use an existing one.

- Access the API Key: Depending on your API's configuration, you may need to create an API key or obtain access credentials.

- paste the api key in .env file


## 5. Create Firebase realtime database
1.Create a Firebase Project
 - Go to the Firebase Console.

- Click Add Project and follow the instructions to create a new Firebase project.

2.Set Up Firebase in Your Project
- Once your project is created, click on Realtime Database in the left-hand menu.

- Click Create Database to set up the Realtime Database.

- Choose a location for your database.

3.Copy your database url and paste in the .env file


## 6. Run the flask 
- Run the flask app using   ```flask run --host=0.0.0.0 --port=5000```


