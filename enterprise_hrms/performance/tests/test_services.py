from django.test import TestCase
from ..services import calculate_final_rating, recommend_increment, recommend_promotion

class ServiceTests(TestCase):
    def test_calculate_final_rating(self):
        # (Self Rating × 20%) + (Manager Rating × 60%) + (Goal Achievement × 20%)
        # (4.0 * 0.2) + (3.5 * 0.6) + (4.0 * 0.2) = 0.8 + 2.1 + 0.8 = 3.7
        rating = calculate_final_rating(4.0, 3.5, 4.0)
        self.assertEqual(rating, 3.7)

    def test_recommend_increment(self):
        self.assertEqual(recommend_increment(1.5), 0.0)
        self.assertEqual(recommend_increment(2.5), 5.0)
        self.assertEqual(recommend_increment(3.5), 10.0)
        self.assertEqual(recommend_increment(4.2), 20.0)
        self.assertEqual(recommend_increment(4.8), 30.0)

    def test_recommend_promotion(self):
        self.assertFalse(recommend_promotion(4.4))
        self.assertTrue(recommend_promotion(4.5))
        self.assertTrue(recommend_promotion(5.0))
