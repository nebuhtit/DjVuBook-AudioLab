import unittest

from speech_text import chunks, normalize_numbers


class SpeechTextTests(unittest.TestCase):
    def test_numbers_are_spelled_in_russian_by_default(self):
        self.assertEqual(normalize_numbers("В 2025 году 21, 3,14%.", "ru"), "В две тысячи двадцать пять году двадцать один, три запятая один четыре процента.")

    def test_numbers_are_spelled_in_english(self):
        self.assertEqual(normalize_numbers("There are 2000 books and 42 pages.", "en"), "There are two thousand books and forty-two pages.")

    def test_number_reading_can_be_disabled(self):
        self.assertEqual(normalize_numbers("Chapter 12, page 4.", "en", False), "Chapter, page.")

    def test_chunks_apply_number_reading_option(self):
        self.assertIn("сорок два", " ".join(part for part, _ in chunks("42 страницы")))
        self.assertNotRegex(" ".join(part for part, _ in chunks("42 страницы", read_numbers=False)), r"\d")
    def test_short_pauses_follow_commas_and_closing_marks(self):
        units = chunks("Первое, второе (третье) и «четвёртое», конец.", punctuation_pause=0.3)
        self.assertEqual([text for text, _ in units], ["Первое,", "второе (третье)", "и «четвёртое»,", "конец."])
        self.assertEqual([pause for _, pause in units], [0.3, 0.3, 0.3, 0.0])

    def test_sentence_paragraph_and_final_pauses_keep_their_roles(self):
        units = chunks("Фраза. Следующая.\n\nНовый абзац.", sentence_pause=0.6, paragraph_pause=1.8)
        self.assertEqual([pause for _, pause in units], [0.6, 1.8, 0.0])

    def test_closing_quote_stays_with_sentence_end(self):
        units = chunks("Он ответил: «Готово.» Потом продолжил.", sentence_pause=0.6)
        self.assertEqual(units[0][0], "Он ответил:")
        self.assertEqual(units[1], ("«Готово.»", 0.6))
        self.assertEqual(units[2][0], "Потом продолжил.")


if __name__ == "__main__":
    unittest.main()
