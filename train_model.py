import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import joblib
import os
import sys
from sklearn.model_selection import train_test_split

def train_model():
    """Train and save the symptom-medicine prediction model"""
    
    print("=" * 60)
    print("🤖 Training Smart Pharma Assistant AI Model")
    print("=" * 60)
    
    # Create sample dataset
    print("\n📊 Creating training dataset...")
    data = {
        'symptoms': [
            'headache fever',
            'cough cold sore throat',
            'stomach pain acidity',
            'allergy itching rash',
            'body pain muscle pain',
            'fever chills',
            'cold runny nose sneezing',
            'acidity heartburn',
            'headache migraine',
            'cough chest congestion',
            'fever headache body pain',
            'sore throat difficulty swallowing',
            'stomach pain diarrhea',
            'skin rash itching',
            'joint pain inflammation',
            'nasal congestion sinus',
            'nausea vomiting',
            'toothache dental pain',
            'eye irritation redness',
            'ear pain infection',
            # Additional samples for better accuracy
            'migraine severe headache',
            'common cold sneezing',
            'gastric problem acidity',
            'skin allergy hives',
            'back pain muscle spasm',
            'viral fever temperature',
            'sinus headache pressure',
            'indigestion bloating',
            'muscle cramps pain',
            'bronchitis cough',
            'arthritis joint swelling',
            'conjunctivitis red eyes',
            'ear infection discharge',
            'urinary infection burning',
            'asthma breathing difficulty',
        ],
        'medicine': [
            'Paracetamol',
            'Combiflam',
            'Cetirizine',
            'Omeprazole',
            'Aspirin',
            'Paracetamol',
            'Cetirizine',
            'Omeprazole',
            'Aspirin',
            'Ambroxol',
            'Paracetamol',
            'Azithromycin',
            'Loperamide',
            'Cetirizine',
            'Ibuprofen',
            'Pseudoephedrine',
            'Domperidone',
            'Diclofenac',
            'Chloramphenicol',
            'Amoxicillin',
            'Sumatriptan',
            'Chlorpheniramine',
            'Pantoprazole',
            'Fexofenadine',
            'Diclofenac Gel',
            'Ibuprofen',
            'Pseudoephedrine',
            'Simethicone',
            'Magnesium Supplement',
            'Salbutamol',
            'Naproxen',
            'Antibiotic Eye Drops',
            'Ciprofloxacin Ear Drops',
            'Nitrofurantoin',
            'Salbutamol Inhaler',
        ]
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create directories if they don't exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    
    # Save dataset
    df.to_csv('data/symptom_medicine.csv', index=False)
    print(f"✅ Created dataset with {len(df)} samples")
    print(f"📁 Saved to: data/symptom_medicine.csv")
    
    # Display dataset info
    print(f"\n📈 Dataset Statistics:")
    print(f"   - Total samples: {len(df)}")
    print(f"   - Unique medicines: {df['medicine'].nunique()}")
    print(f"   - Medicine distribution:")
    medicine_counts = df['medicine'].value_counts()
    for med, count in medicine_counts.items():
        print(f"      • {med}: {count} samples")
    
    # Train model
    print("\n🤖 Training ML model...")
    X = df['symptoms']
    y = df['medicine']
    
    # Split data for validation
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Create and train model pipeline
    model = make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 2),  # Use single words and bigrams
            max_features=100,
            stop_words='english'
        ),
        MultinomialNB(alpha=0.1)  # Regularization
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"✅ Model trained successfully!")
    print(f"📊 Model Accuracy:")
    print(f"   - Training set: {train_score:.2%}")
    print(f"   - Test set: {test_score:.2%}")
    
    # Save model
    model_path = 'models/symptom_model.joblib'
    joblib.dump(model, model_path)
    print(f"💾 Model saved to: {model_path}")
    
    # Test predictions
    print("\n🧪 Test Predictions:")
    test_cases = [
        ('headache fever', 'Expected: Paracetamol'),
        ('cough cold', 'Expected: Combiflam or Ambroxol'),
        ('stomach pain acidity', 'Expected: Omeprazole'),
        ('allergy rash', 'Expected: Cetirizine'),
        ('joint pain inflammation', 'Expected: Ibuprofen'),
    ]
    
    for symptoms, expected in test_cases:
        try:
            prediction = model.predict([symptoms])[0]
            probabilities = model.predict_proba([symptoms])[0]
            confidence = probabilities.max() * 100
            predicted_class_idx = probabilities.argmax()
            top_3_indices = probabilities.argsort()[-3:][::-1]
            top_3 = [(model.classes_[i], probabilities[i] * 100) 
                    for i in top_3_indices]
            
            print(f"\n  Symptoms: '{symptoms}'")
            print(f"  {expected}")
            print(f"  🔍 Prediction: {prediction} ({confidence:.1f}% confidence)")
            print(f"  🏆 Top 3 recommendations:")
            for med, conf in top_3:
                print(f"     • {med}: {conf:.1f}%")
                
        except Exception as e:
            print(f"  Error predicting '{symptoms}': {str(e)}")
    
    # Feature importance (for debugging/insights)
    print("\n🔍 Model Insights:")
    vectorizer = model.named_steps['tfidfvectorizer']
    classifier = model.named_steps['multinomialnb']
    
    feature_names = vectorizer.get_feature_names_out()
    
    print("  Most important symptoms for each medicine:")
    for i, medicine in enumerate(model.classes_):
        top_features_idx = classifier.feature_log_prob_[i].argsort()[-5:][::-1]
        top_features = [feature_names[idx] for idx in top_features_idx]
        print(f"    • {medicine}: {', '.join(top_features)}")
    
    print("\n" + "=" * 60)
    print("✅ Model training completed successfully!")
    print("=" * 60)
    
    return model

if __name__ == '__main__':
    try:
        model = train_model()
        
        # Verify the model can be loaded
        print("\n🔍 Verifying model can be loaded...")
        loaded_model = joblib.load('models/symptom_model.joblib')
        print("✅ Model verification successful!")
        
        # Print next steps
        print("\n" + "=" * 60)
        print("🚀 NEXT STEPS:")
        print("=" * 60)
        print("1. Run database initialization:")
        print("   python init_db.py")
        print("\n2. Start the Flask application:")
        print("   python app.py")
        print("\n3. Open your browser and go to:")
        print("   http://127.0.0.1:5000")
        print("\n4. Login with:")
        print("   Username: admin")
        print("   Password: admin123")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error training model: {str(e)}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Install required packages:")
        print("   pip install pandas scikit-learn joblib")
        print("\n2. Check Python version (requires 3.7+):")
        print("   python --version")
        print("\n3. Ensure you have write permissions in the current directory")
        sys.exit(1)