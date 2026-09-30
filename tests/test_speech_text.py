import unittest

from speech_text import chunks


class SpeechTextTests(unittest.TestCase):
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
