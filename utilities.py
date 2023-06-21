RUBRIC_HEADER = (
    "Given a student's self-explanation responses after they've played an educational game about decimal numbers, "
    "label the response according to the following rubric. "
    "Label each response as CORRECT, or INCORRECT. "
    "INCORRECT responses deviate from the CORRECT answer, use incorrect reasoning, "
    "are irrelevant, or do not directly answer the question. "
    "If a response gives a correct explanation but not an explicit answer it should be labeled as CORRECT. "
    "Note: Typos or grammatical errors should not be considered in the rubric "
    "unless they affect the correctness of the answer."
)

def get_question_type(row):
    se_question = row["Question"]

    match se_question:
        # type 1A
        case "Is 0.2 bigger or smaller than 0.22? How do you know?":
            return "1A"

        case "Is 1.6452 bigger or smaller than 1.29? How do you know?":
            return "1A"

        case "Is 1.4 bigger or smaller than 1.51? How do you know?":
            return "1A"
        
        case "Is 9.2111 bigger or smaller than 9.222? How do you know?":
            return "1A"

        case "Is 1.05 bigger or smaller than 1.2215? How do you know?":
            return "1A"

        case "Is 1.0111 bigger or smaller than 1.1? How do you know?":
            return "1A"

        case "Is 0.1112 bigger or smaller than 0.03? How do you know?":
            return "1A"
        
        case "Is 6.5 bigger or smaller than 6.41? How do you know?":
            return "1A"
        
        # type 1B
        case "Is -1.701 bigger or smaller than -1.7? How do you know?":
            return "1B"
        
        # type 1C
        case "Is -8.517 bigger or smaller than 8.5? How do you know?":
            return "1C"

        case "Is -0.9 bigger or smaller than 0.6? How do you know?":
            return "1C"

        case "Is 0.32 bigger or smaller than -0.519? How do you know?":
            return "1C"

        # type 2
        case "Is 0.456 to the left of 0 or to the right of 0 on the number line? How do you know?":
            return "2"

        case "Is 0.579 to the left of 0 or to the right of 0 on the number line? How do you know?":
            return "2"

        case "Is 0.111 to the left of 0 or to the right of 0 on the number line? How do you know?":
            return "2"

        # type 3
        case "Is 0.042 closer to 0 or closer to 0.5? How do you know?":
            return "3"

        case "Is 0.091 closer to 0 or closer to 1? How do you know?":
            return "3"

        case "Is -0.07 closer to 0 or closer to -1? How do you know?":
            return "3"

        # type 4
        case "How do you figure how what a sequence is changing by?\n":
            return "4"

        # type 5
        case "What should you remember to find the next number in the sequence?":
            return "5"

        # type 6
        case "The next number in the pattern can be found by adding 17.6 + 4.4. What is the answer and how do you know?":
            return "6"

        # type 7
        case "When should you carry? How do you know?":
            return "7"

        # type 8
        case "What should you do whenever there is more than 10 in any column? How do you know?":
            return "8"

        # type 9
        case "When adding two decimal numbers, how should you line up the numbers and add them?":
            return "9"

        # else
        case _:
            return "undefined"


def convert_rubric_item_to_text(row):
    question_type, rubric = row["Question Type"], row["Rubric"]
    return f"Question Type: {question_type}\nRubric: {rubric}"


def convert_full_rubric_to_text(df_rubric):
    rubric_texts = df_rubric.apply(convert_rubric_item_to_text, axis = 1)
    return " \n".join(rubric_texts)
