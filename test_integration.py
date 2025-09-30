#!/usr/bin/env python3
"""
Integration tests dla Half Marathon Predictor
Testuje pełny flow z prawdziwym modelem
"""

import os
import sys
import unittest
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestFullIntegration(unittest.TestCase):
    """Integration tests z prawdziwym modelem i API"""
    
    @classmethod
    def setUpClass(cls):
        """Setup raz przed wszystkimi testami"""
        from utils.model_predictor import HalfMarathonPredictor
        from utils.llm_extractor import extract_user_data_auto
        
        cls.predictor = HalfMarathonPredictor()
        cls.extractor = extract_user_data_auto
    
    def test_full_flow_simple_input(self):
        """Test pełnego flow z prostym inputem"""
        user_input = "M 30 lat, 5km 24:30"
        
        # Extract
        extracted = self.extractor(user_input)
        
        self.assertEqual(extracted['gender'], 'male')
        self.assertEqual(extracted['age'], 30)
        self.assertEqual(extracted['time_5km_seconds'], 1470)
        
        # Predict
        result = self.predictor.predict(extracted)
        
        self.assertTrue(result['success'])
        self.assertIn('formatted_time', result)
        self.assertGreater(result['prediction_seconds'], 3600)  # > 1h
        self.assertLess(result['prediction_seconds'], 14400)    # < 4h
    
    def test_full_flow_complex_input(self):
        """Test z bardziej skomplikowanym inputem"""
        user_input = "Jestem 28-letnią kobietą, mój najlepszy czas na 5 kilometrów to 27 minut i 15 sekund"
        
        extracted = self.extractor(user_input)
        
        self.assertEqual(extracted['gender'], 'female')
        self.assertEqual(extracted['age'], 28)
        
        result = self.predictor.predict(extracted)
        self.assertTrue(result['success'])
    
    def test_model_consistency(self):
        """Test czy model daje spójne wyniki"""
        test_data = {
            'gender': 'male',
            'age': 30,
            'time_5km_seconds': 1470
        }
        
        # Wywołaj 3 razy - powinno dać te same wyniki
        results = [self.predictor.predict(test_data) for _ in range(3)]
        
        times = [r['prediction_seconds'] for r in results]
        
        # Wszystkie wyniki powinny być identyczne
        self.assertEqual(len(set(times)), 1, "Model daje różne wyniki dla tych samych danych!")
    
    def test_edge_cases(self):
        """Test przypadków brzegowych"""
        edge_cases = [
            {'gender': 'male', 'age': 18, 'time_5km_seconds': 900},   # Bardzo szybki młody
            {'gender': 'female', 'age': 70, 'time_5km_seconds': 2400}, # Starsza wolniejsza
            {'gender': 'male', 'age': 45, 'time_5km_seconds': 1800},  # Średni wiek, wolny
        ]
        
        for case in edge_cases:
            result = self.predictor.predict(case)
            self.assertTrue(result['success'], f"Failed for case: {case}")
            self.assertGreater(result['prediction_seconds'], 3600)
            self.assertLess(result['prediction_seconds'], 14400)
    
    def test_regex_vs_llm(self):
        """Test czy REGEX działa dla prostych przypadków"""
        from utils.llm_extractor import _preparse_quick
        
        simple_inputs = [
            "M 30 lat, 5km 24:30",
            "K 25 lat, 5k 27:00",
            "Male 45 years, 5km 22:30"
        ]
        
        for inp in simple_inputs:
            quick = _preparse_quick(inp)
            # REGEX powinien złapać wszystkie 3 pola
            self.assertIsNotNone(quick['gender'], f"REGEX failed for: {inp}")
            self.assertIsNotNone(quick['age'], f"REGEX failed for: {inp}")
            self.assertIsNotNone(quick['time_5km_seconds'], f"REGEX failed for: {inp}")


class TestModelMetadata(unittest.TestCase):
    """Test metadanych modelu"""
    
    def test_model_has_metadata(self):
        """Sprawdź czy model ma metadata"""
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        
        self.assertIsNotNone(predictor.model_metadata)
        self.assertIn('version', predictor.model_metadata)
        self.assertIn('source', predictor.model_metadata)
    
    def test_feature_order_consistency(self):
        """Sprawdź czy feature_order jest spójne"""
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        
        if predictor.model is not None:
            # Jeśli model załadowany, sprawdź feature_order
            self.assertIsNotNone(predictor.feature_order, 
                "Model załadowany ale brak feature_order!")
            self.assertIsInstance(predictor.feature_order, list)
            self.assertGreater(len(predictor.feature_order), 0)
            print(f"✅ Feature order: {predictor.feature_order}")


class TestCaching(unittest.TestCase):
    """Test mechanizmów cache"""
    
    def test_llm_cache_works(self):
        """Sprawdź czy cache LLM działa"""
        from utils.llm_extractor import extract_user_data, _cached_llm_call
        
        # Wyczyść cache
        _cached_llm_call.cache_clear()
        
        text = "M 30 lat, 5km 24:30"
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Pierwsze wywołanie
        result1 = _cached_llm_call(text, model)
        cache_info1 = _cached_llm_call.cache_info()
        
        # Drugie wywołanie (powinno użyć cache)
        result2 = _cached_llm_call(text, model)
        cache_info2 = _cached_llm_call.cache_info()
        
        # Wyniki powinny być identyczne
        self.assertEqual(result1, result2)
        
        # Cache hit powinien wzrosnąć
        self.assertEqual(cache_info2.hits, cache_info1.hits + 1)
        print(f"✅ Cache hit ratio: {cache_info2.hits}/{cache_info2.hits + cache_info2.misses}")


class TestErrorHandling(unittest.TestCase):
    """Test obsługi błędów"""
    
    def test_invalid_gender(self):
        """Test z nieprawidłową płcią"""
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        result = predictor.predict({
            'gender': 'unknown',
            'age': 30,
            'time_5km_seconds': 1470
        })
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('hint', result)
    
    def test_invalid_age(self):
        """Test z nieprawidłowym wiekiem"""
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        
        # Za młody
        result = predictor.predict({
            'gender': 'male',
            'age': 10,
            'time_5km_seconds': 1470
        })
        self.assertFalse(result['success'])
        
        # Za stary
        result = predictor.predict({
            'gender': 'male',
            'age': 100,
            'time_5km_seconds': 1470
        })
        self.assertFalse(result['success'])
    
    def test_invalid_time(self):
        """Test z nieprawidłowym czasem"""
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        
        # Za szybko (< 9 min)
        result = predictor.predict({
            'gender': 'male',
            'age': 30,
            'time_5km_seconds': 400
        })
        self.assertFalse(result['success'])
        
        # Za wolno (> 60 min)
        result = predictor.predict({
            'gender': 'male',
            'age': 30,
            'time_5km_seconds': 4000
        })
        self.assertFalse(result['success'])


class TestPerformance(unittest.TestCase):
    """Test wydajności"""
    
    def test_prediction_speed(self):
        """Test czy predykcja jest szybka"""
        import time
        from utils.model_predictor import HalfMarathonPredictor
        
        predictor = HalfMarathonPredictor()
        test_data = {
            'gender': 'male',
            'age': 30,
            'time_5km_seconds': 1470
        }
        
        start = time.time()
        result = predictor.predict(test_data)
        duration = time.time() - start
        
        self.assertTrue(result['success'])
        self.assertLess(duration, 1.0, "Predykcja trwa za długo (>1s)!")
        print(f"✅ Prediction time: {duration*1000:.2f}ms")
    
    def test_extraction_speed(self):
        """Test czy ekstrakcja REGEX jest szybka"""
        import time
        from utils.llm_extractor import _preparse_quick
        
        text = "M 30 lat, 5km 24:30"
        
        start = time.time()
        result = _preparse_quick(text)
        duration = time.time() - start
        
        self.assertLess(duration, 0.1, "REGEX parsing trwa za długo (>100ms)!")
        print(f"✅ REGEX extraction time: {duration*1000:.2f}ms")


def run_integration_tests():
    """Uruchom wszystkie testy integracyjne"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Dodaj wszystkie test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFullIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestModelMetadata))
    suite.addTests(loader.loadTestsFromTestCase(TestCaching))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    print("="*60)
    print("  HALF MARATHON PREDICTOR - INTEGRATION TESTS")
    print("="*60)
    print()
    
    exit_code = run_integration_tests()
    
    print()
    if exit_code == 0:
        print("✅ Wszystkie testy integracyjne przeszły!")
    else:
        print("❌ Niektóre testy nie przeszły")
    
    sys.exit(exit_code)