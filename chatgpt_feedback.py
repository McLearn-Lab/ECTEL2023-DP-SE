import sys, os, time
import pandas as pd
from chatgpt_wrapper import ChatGPT
from utilities import RUBRIC_HEADER, get_question_type

def build_feedback_prompt(row):
	"""
	Constructs an input query to ChatGPT, referring to the
	self explanation question and the student response.

	arg:
		row (pd.Series) : a row in the merged dataset, containing the
			problem name, PS question, SE question and student response

	returns:
		str - the string query to ChatGPT
	"""

	template = """
		Suppose you are a middle school math teacher and you are currently teaching decimals.
		You want to grade students’ explanations for how they solved a decimal question,
		as directed by a prepared question you wrote ahead of time.
		Given that question, a small rubric explaining the requirements for a correct answer,
		and the student's incorrect answer, please provide a clear and concise 1-3 sentences
		of feedback to the student about why their answer is incorrect
		and direct them to the correct answer.

		Here is the self-explanation question: '{se_question}'
		Here is the rubric for grading this question: '{rubric}'
		Here is the student's response: '{student_answer}'
	"""

	return template.format(
		se_question = row["Question"],
		rubric = row["Rubric"],
		student_answer = row["Answer"]
	)

def query_response(df, bot, start_index, end_index):
	"""
	Send a subset of the data to ChatGPT and save the output in a checkpont csv file.

	args:
		df (pd.DataFrame) : the full input dataframe
		bot (ChatGPT) : an instance of the ChatGPT class from the Wrapper API
		start_index (int) : the index of the first row of data to send
		end_index (int) : the index of the last row of data to send (exclusive)

	returns:
		boolean - an indicator of whether a checkpoint CSV file
			was successfully generated. If this is False, you have reached
			the request limit by ChatGPT.
	"""
	responses = []
	df_subset = df.loc[start_index : min(len(df),end_index), :].reset_index()

	for index, row in df_subset.iterrows():
		if row["Code"] == 'INCORRECT': #Human coding, not GPT coding
			success, response, message = bot.ask(build_feedback_prompt(row))
			if success:
				responses.append(response)
			else:
				print("Error at line", start_index + index, "with message", message)
				responses.append("")
				if len(responses) == 1:
					return False
			time.sleep(0.5)
		else:
			responses.append("")

	df_subset["ChatGPT Feedback"] = responses
	df_subset.to_csv(f"output/chatgpt_feedback_{start_index:04d}_{end_index:04d}.csv", index = False)
	print(f"Finished querying chatgpt from row {start_index} to {end_index}")
	return True


def main(starting_page, n_rows_per_page = 100):
	"""
	Use the ChatGPT wrapper to send queries to ChatGPT and
	record its responses to a new csv file called chatgpt_feedback.csv
	
	args:
		starting_page (int) : the index of the starting page, with each page
			containing n_rows_per_page rows. For example if starting_page = 5,
			the first 5*n_rows_per_page rows in the input dataframe are skipped

		n_rows_per_page (int) : the number of rows to collect in a page
	"""
	df_input = pd.read_csv("output/chatgpt_labels.csv")
	df_rubric = pd.read_csv("grading_rubric.csv")
	df_input["Question Type"] = df_input.apply(get_question_type, axis = 1)
	df_input = df_input.merge(df_rubric)
	bot = ChatGPT()

	for start in range(starting_page*n_rows_per_page, len(df_input), n_rows_per_page):
		success = query_response(df_input, bot, start, start + n_rows_per_page)

		# when the message cap has been reached, wait for a bit more than 1 hour
		# then repeat the previous request
		if not success:
			print("Message cap reached. Waiting for 4000s ...")
			time.sleep(4000)
			print("Waiting finished. Now attempting to repeat the previous request")
			bot = ChatGPT()
			assert query_response(df_input, bot, start, start + n_rows_per_page)


if __name__ == '__main__':
	starting_page = int(sys.argv[1]) if len(sys.argv) > 1 else 0
	if not os.path.exists("output"):
		os.mkdir("output")

	main(starting_page)