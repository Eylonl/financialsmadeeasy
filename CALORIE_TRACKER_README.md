# 🍽️ AI Calorie Tracker

A Streamlit web application that uses OpenAI's GPT-4 Vision to analyze food photos and estimate calories.

## Features

- **Photo Analysis**: Take photos with your iPhone camera or upload images
- **AI Food Recognition**: GPT-4 Vision identifies foods, portions, and estimates calories
- **User Confirmation**: Review and edit AI results before saving
- **Meal History**: Track meals by date with persistent storage
- **Daily Summaries**: View daily calorie totals and trends
- **Goal Tracking**: Set daily calorie goals with progress tracking

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r calorie_requirements.txt
```

### 2. Get OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy the key (you'll enter it in the app)

### 3. Run the App
```bash
streamlit run calorie_tracker_app.py
```

### 4. Using the App
1. Enter your OpenAI API key in the sidebar
2. Select meal type (Breakfast, Lunch, Dinner, Snack)
3. Take a photo using your iPhone camera or upload an image
4. Click "Analyze Food" to get AI analysis
5. Review and edit the results if needed
6. Click "Confirm & Save Meal" to add to your history

## iPhone Camera Integration

The app uses Streamlit's built-in camera input which works seamlessly with iPhone browsers:
- Open the app in Safari or Chrome on your iPhone
- When you click "Take a picture", it will access your camera
- Take the photo and it will automatically upload for analysis

## Data Storage

- Meal history is stored locally in `meal_history.json`
- Data persists between app sessions
- Easy to backup or transfer your data

## Deployment to Streamlit Cloud

When ready to deploy:
1. Push your code to GitHub
2. Connect to Streamlit Community Cloud
3. Add your OpenAI API key as a secret in the deployment settings

## Tips for Best Results

- Take clear, well-lit photos of your meals
- Include the entire plate/meal in the photo
- Review AI estimates - they're helpful starting points but may need adjustment
- Use consistent portion descriptions for better tracking
