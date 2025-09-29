"""
Unit tests for Half Marathon Predictor
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_extractor import parse_time_to_seconds
from utils.model_predictor import HalfMarathonPredictor


class TestTimeParser(unittest.TestCase):
    """Test time parsing functions"""
    
    def test_parse_mm_ss_format(self):
        """Test MM:SS format"""
        self.assertEqual(parse_time_to_seconds("24:30"), 1470)
        self.assertEqual(parse_time_to_seconds("23:45"), 1425)
        
    def test_parse_hh_mm_ss_format(self):
        """Test HH:MM:SS format"""
        self.assertEqual(parse_time_to_seconds("0:24:30"), 1470)
        self.assertEqual(parse_time_to_seconds("1:00:00"), 3600)
        
    def test_parse_minutes_only(self):
        """Test minutes as number"""
        self.assertEqual(parse_time_to_seconds("24"), 1440)
        self.assertEqual(parse_time_to_seconds("30"), 1800)
        
    def test_parse_with_words(self):
        """Test with 'minutes' text"""
        self.assertEqual(parse_time_to_seconds("24 minutes"), 1440)
        self.assertEqual(parse_time_to_seconds("25 min"), 1500)
        
    def test_invalid_input(self):
        """Test invalid inputs"""
        self.assertIsNone(parse_time_to_seconds("invalid"))
        self.assertIsNone(parse_time_to_seconds(""))


class TestDataExtraction(unittest.TestCase):
    """Test LLM data extraction"""
    
    @patch('utils.llm_extractor.client')
    def test_extract_complete_data(self, mock_client):
        """Test extraction with complete information"""
        from utils.llm_extractor import extract_user_data
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "gender": "male",
            "age": 30,
            "time_5km_seconds": 1470
        }
        '''
        mock_response.usage.total_tokens = 100
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_user_data("I'm a 30-year-old male, 5km time is 24:30")
        
        self.assertEqual(result['gender'], 'male')
        self.assertEqual(result['age'], 30)
        self.assertEqual(result['time_5km_seconds'], 1470)
    
    @patch('utils.llm_extractor.client')
    def test_extract_missing_data(self, mock_client):
        """Test extraction with missing information"""
        from utils.llm_extractor import extract_user_data
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "gender": "male",
            "age": null,
            "time_5km_seconds": null
        }
        '''
        mock_response.usage.total_tokens = 80
        mock_client.chat.completions.create.return_value = mock_response
        
        result = extract_user_data("I'm a male runner")
        
        self.assertEqual(result['gender'], 'male')
        self.assertIsNone(result['age'])
        self.assertIsNone(result['time_5km_seconds'])


class TestModelPredictor(unittest.TestCase):
    """Test model prediction functionality"""
    
    def test_valid_prediction_input(self):
        """Test prediction with valid input"""
        # This test requires actual model, so we mock it
        predictor = HalfMarathonPredictor()
        
        # Mock the model
        with patch.object(predictor, 'model') as mock_model:
            mock_model.predict.return_value = [6300]  # 1:45:00
            
            result = predictor.predict({
                'gender': 'male',
                'age': 30,
                'time_5km_seconds': 1470
            })
            
            self.assertTrue(result['success'])
            self.assertEqual(result['hours'], 1)
            self.assertEqual(result['minutes'], 45)
            self.assertIsNotNone(result['formatted_time'])
    
    def test_invalid_prediction_input(self):
        """Test prediction with invalid input"""
        predictor = HalfMarathonPredictor()
        
        result = predictor.predict({
            'gender': 'male'
            # Missing age and time
        })
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_gender_encoding(self):
        """Test gender encoding logic"""
        predictor = HalfMarathonPredictor()
        
        with patch.object(predictor, 'model') as mock_model:
            mock_model.predict.return_value = [6000]
            
            # Test male encoding
            predictor.predict({
                'gender': 'male',
                'age': 30,
                'time_5km_seconds': 1400
            })
            
            # Test female encoding
            predictor.predict({
                'gender': 'female',
                'age': 28,
                'time_5km_seconds': 1500
            })


class TestModelFormats(unittest.TestCase):
    """Test output formatting"""
    
    def test_time_formatting(self):
        """Test time format conversion"""
        predictor = HalfMarathonPredictor()
        
        with patch.object(predictor, 'model') as mock_model:
            # Test 1:30:00
            mock_model.predict.return_value = [5400]
            result = predictor.predict({
                'gender': 'male',
                'age': 25,
                'time_5km_seconds': 1200
            })
            self.assertEqual(result['formatted_time'], '1:30:00')
            
            # Test 2:15:30
            mock_model.predict.return_value = [8130]
            result = predictor.predict({
                'gender': 'female',
                'age': 35,
                'time_5km_seconds': 1800
            })
            self.assertEqual(result['formatted_time'], '2:15:30')
    
    def test_pace_calculation(self):
        """Test average pace calculation"""
        predictor = HalfMarathonPredictor()
        
        with patch.object(predictor, 'model') as mock_model:
            mock_model.predict.return_value = [6300]  # 1:45:00
            
            result = predictor.predict({
                'gender': 'male',
                'age': 30,
                'time_5km_seconds': 1470
            })
            
            # 6300 seconds / 21.0975 km / 60 = pace in min/km
            expected_pace = 6300 / 21.0975 / 60
            self.assertAlmostEqual(
                result['average_pace_min_per_km'],
                expected_pace,
                places=2
            )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_very_fast_time(self):
        """Test with elite runner times"""
        predictor = HalfMarathonPredictor()
        
        with patch.object(predictor, 'model') as mock_model:
            mock_model.predict.return_value = [3900]  # ~1:05:00
            
            result = predictor.predict({
                'gender': 'male',
                'age': 25,
                'time_5km_seconds': 900  # 15:00 for 5km
            })
            
            self.assertTrue(result['success'])
            self.assertLess(result['prediction_seconds'], 4000)
    
    def test_slow_time(self):
        """Test with beginner runner times"""
        predictor = HalfMarathonPredictor()
        
        with patch.object(predictor, 'model') as mock_model:
            mock_model.predict.return_value = [9000]  # 2:30:00
            
            result = predictor.predict({
                'gender': 'female',
                'age': 50,
                'time_5km_seconds': 2100  # 35:00 for 5km
            })
            
            self.assertTrue(result['success'])
            self.assertGreater(result['prediction_seconds'], 7200)
    
    def test_age_boundaries(self):
        """Test with various ages"""
        predictor = HalfMarathonPredictor()
        
        with patch.object(predictor, 'model') as mock_model:
            mock_model.predict.return_value = [6000]
            
            # Young runner
            result = predictor.predict({
                'gender': 'male',
                'age': 18,
                'time_5km_seconds': 1400
            })
            self.assertTrue(result['success'])
            
            # Older runner
            result = predictor.predict({
                'gender': 'male',
                'age': 70,
                'time_5km_seconds': 1800
            })
            self.assertTrue(result['success'])


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTimeParser))
    suite.addTests(loader.loadTestsFromTestCase(TestDataExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestModelPredictor))
    suite.addTests(loader.loadTestsFromTestCase(TestModelFormats))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_tests()