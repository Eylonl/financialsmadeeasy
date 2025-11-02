import streamlit as st
import openai
from PIL import Image
import base64
import io
import json
import os
from datetime import datetime, date
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Calorie Tracker",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'meal_history' not in st.session_state:
    st.session_state.meal_history = []
if 'daily_totals' not in st.session_state:
    st.session_state.daily_totals = {}

def load_meal_history():
    """Load meal history from JSON file"""
    if os.path.exists('meal_history.json'):
        try:
            with open('meal_history.json', 'r') as f:
                data = json.load(f)
                st.session_state.meal_history = data.get('meals', [])
                st.session_state.daily_totals = data.get('daily_totals', {})
        except Exception as e:
            st.error(f"Error loading meal history: {e}")

def save_meal_history():
    """Save meal history to JSON file"""
    try:
        data = {
            'meals': st.session_state.meal_history,
            'daily_totals': st.session_state.daily_totals
        }
        with open('meal_history.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving meal history: {e}")

def encode_image(image):
    """Convert PIL image to base64 string for OpenAI API"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def analyze_food_with_openai(image, api_key):
    """Analyze food image using OpenAI GPT-4 Vision"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Convert image to base64
        base64_image = encode_image(image)
        
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this food image and provide a detailed breakdown. Return your response in the following JSON format:
                            {
                                "foods": [
                                    {
                                        "name": "food item name",
                                        "portion_size": "estimated portion (e.g., '1 cup', '150g', '1 medium')",
                                        "calories": estimated_calories_number,
                                        "confidence": confidence_percentage
                                    }
                                ],
                                "total_calories": total_estimated_calories,
                                "notes": "any additional observations about the meal"
                            }
                            
                            Be as accurate as possible with portion sizes and calorie estimates. If you're unsure, indicate lower confidence."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        # Parse the JSON response
        response_text = response.choices[0].message.content
        
        # Extract JSON from response (in case there's extra text)
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        json_str = response_text[start_idx:end_idx]
        
        return json.loads(json_str)
        
    except Exception as e:
        st.error(f"Error analyzing image: {e}")
        return None

def add_meal_to_history(meal_data, meal_type):
    """Add confirmed meal to history"""
    today = date.today().isoformat()
    
    meal_entry = {
        'date': today,
        'timestamp': datetime.now().isoformat(),
        'meal_type': meal_type,
        'foods': meal_data['foods'],
        'total_calories': meal_data['total_calories'],
        'notes': meal_data.get('notes', '')
    }
    
    st.session_state.meal_history.append(meal_entry)
    
    # Update daily totals
    if today not in st.session_state.daily_totals:
        st.session_state.daily_totals[today] = 0
    st.session_state.daily_totals[today] += meal_data['total_calories']
    
    save_meal_history()

def main():
    # Load meal history on startup
    load_meal_history()
    
    st.title("🍽️ AI Calorie Tracker")
    st.markdown("Take a photo of your meal and let AI estimate the calories!")
    
    # Sidebar for API key and settings
    with st.sidebar:
        st.header("Settings")
        
        # Try to get API key from secrets first (for deployment), then from user input
        api_key = None
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except:
            api_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key")
        
        if not api_key:
            st.warning("Please enter your OpenAI API key to use the app")
            return
        
        st.header("Daily Summary")
        today = date.today().isoformat()
        today_calories = st.session_state.daily_totals.get(today, 0)
        st.metric("Today's Calories", f"{today_calories:.0f}")
        
        # Daily goal (optional)
        daily_goal = st.number_input("Daily Calorie Goal (optional)", min_value=0, value=2000)
        if daily_goal > 0:
            progress = min(today_calories / daily_goal, 1.0)
            st.progress(progress)
            remaining = max(daily_goal - today_calories, 0)
            st.write(f"Remaining: {remaining:.0f} calories")
    
    # Main content tabs
    tab1, tab2 = st.tabs(["📸 Add Meal", "📊 History"])
    
    with tab1:
        st.header("Add New Meal")
        
        # Meal type selection
        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
        
        # Camera input
        st.subheader("Take a Photo")
        camera_image = st.camera_input("Take a picture of your meal")
        
        # File upload as alternative
        st.subheader("Or Upload an Image")
        uploaded_file = st.file_uploader("Choose an image...", type=['jpg', 'jpeg', 'png'])
        
        # Process image
        image_to_analyze = None
        if camera_image is not None:
            image_to_analyze = Image.open(camera_image)
        elif uploaded_file is not None:
            image_to_analyze = Image.open(uploaded_file)
        
        if image_to_analyze is not None:
            # Display the image
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.image(image_to_analyze, caption="Your meal", use_column_width=True)
            
            with col2:
                if st.button("Analyze Food", type="primary"):
                    with st.spinner("Analyzing your meal..."):
                        analysis = analyze_food_with_openai(image_to_analyze, api_key)
                    
                    if analysis:
                        st.session_state.current_analysis = analysis
                        st.session_state.current_meal_type = meal_type
                        st.rerun()
        
        # Display analysis results for confirmation
        if 'current_analysis' in st.session_state:
            st.subheader("AI Analysis Results")
            analysis = st.session_state.current_analysis
            
            st.write("**Detected Foods:**")
            
            # Create editable form for confirmation
            with st.form("confirm_meal"):
                total_calories = 0
                confirmed_foods = []
                
                for i, food in enumerate(analysis['foods']):
                    st.write(f"**{food['name']}**")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        portion = st.text_input(f"Portion Size", value=food['portion_size'], key=f"portion_{i}")
                    with col2:
                        calories = st.number_input(f"Calories", value=food['calories'], min_value=0, key=f"calories_{i}")
                    with col3:
                        confidence = st.slider(f"Confidence", 0, 100, food['confidence'], key=f"confidence_{i}")
                    
                    confirmed_foods.append({
                        'name': food['name'],
                        'portion_size': portion,
                        'calories': calories,
                        'confidence': confidence
                    })
                    total_calories += calories
                
                notes = st.text_area("Additional Notes", value=analysis.get('notes', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Confirm & Save Meal", type="primary"):
                        confirmed_meal = {
                            'foods': confirmed_foods,
                            'total_calories': total_calories,
                            'notes': notes
                        }
                        add_meal_to_history(confirmed_meal, st.session_state.current_meal_type)
                        st.success(f"Meal saved! Total calories: {total_calories}")
                        del st.session_state.current_analysis
                        del st.session_state.current_meal_type
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("Cancel"):
                        del st.session_state.current_analysis
                        del st.session_state.current_meal_type
                        st.rerun()
                
                st.metric("Total Calories", f"{total_calories:.0f}")
    
    with tab2:
        st.header("Meal History")
        
        if not st.session_state.meal_history:
            st.info("No meals recorded yet. Add your first meal in the 'Add Meal' tab!")
        else:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                date_filter = st.date_input("Filter by Date (optional)")
            with col2:
                meal_type_filter = st.selectbox("Filter by Meal Type", ["All", "Breakfast", "Lunch", "Dinner", "Snack"])
            
            # Display meals
            filtered_meals = st.session_state.meal_history
            
            if date_filter:
                filtered_meals = [m for m in filtered_meals if m['date'] == date_filter.isoformat()]
            
            if meal_type_filter != "All":
                filtered_meals = [m for m in filtered_meals if m['meal_type'] == meal_type_filter]
            
            for meal in reversed(filtered_meals):  # Show most recent first
                with st.expander(f"{meal['date']} - {meal['meal_type']} ({meal['total_calories']:.0f} calories)"):
                    st.write(f"**Time:** {meal['timestamp'][:19].replace('T', ' ')}")
                    st.write("**Foods:**")
                    for food in meal['foods']:
                        st.write(f"- {food['name']}: {food['portion_size']} ({food['calories']} calories)")
                    if meal['notes']:
                        st.write(f"**Notes:** {meal['notes']}")
            
            # Daily summary chart
            if st.session_state.daily_totals:
                st.subheader("Daily Calorie Trends")
                df = pd.DataFrame(list(st.session_state.daily_totals.items()), columns=['Date', 'Calories'])
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date')
                st.line_chart(df.set_index('Date'))

if __name__ == "__main__":
    main()
