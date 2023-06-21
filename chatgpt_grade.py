import sys, os, time
import pandas as pd
from chatgpt_wrapper import ChatGPT
from utilities import RUBRIC_HEADER, get_question_type, convert_full_rubric_to_text


def build_chatgpt_prompt_full_rubric(row, full_rubric):
	"""
	Construct an input query to ChatGPT, combining a pre-defined rubric
	and the context around a student response.

	args:
		row (pd.Series) : a row in the merged dataset, containing the
			problem name, PS question, SE question and student response
		full_rubric (Str) : the rubric text that specifies the grading process

	returns:
		str - the string query to ChatGPT
	"""
	template = """
		{header}

		{full_rubric}

		Now I will give you a self-explanation question, and a student's response to this question.

		First determine the type of this question (e.g., Type 1A, Type 5, Type 6), based on the
		patterns specified in the rubric.

		Next, follow the rubric to label the student's response as either 'CORRECT' or 'INCORRECT'. 

		Here is the self-explanation question:

		'{se_question}'

		Here is the student's response:

		'{student_answer}'

		Please answer with only two phrases, separated by a comma.
		The first phrase is the identified question type.
		The second phrase is the CORRECT or INCORRECT label.
		Do not include any additional information.

		Here is an example answer I expect from you:

		Question Type 2A,CORRECT
	"""

	return template.format(
		header = RUBRIC_HEADER,
		full_rubric = full_rubric,
		ps_question = row["Problem-solving Question"], 
		se_question = row["Question"], 
		student_answer = row["Answer"]
	)


def build_chatgpt_prompt_individual_rubric(row):
	template = """
		{header}

		Here is the self-explanation question:

		'{se_question}'

		Here is the student's response:

		'{student_answer}'

		Here is the rubric for grading this question: {rubric}

		Please answer with only a single word: 'CORRECT' or 'INCORRECT'. Do not include any additional information.
	"""

	return template.format(
		header = RUBRIC_HEADER,
		ps_question = row["Problem-solving Question"],
		se_question = row["Question"],
		rubric = row["Rubric"],
		student_answer = row["Answer"]
	)


def query_response(df, bot, rubric_mode, full_rubric, start_index, end_index, output_name = None):
	"""
	Send a subset of the data to ChatGPT and save the output in a checkpont csv file.

	args:
		df (pd.DataFrame) : the full input dataframe
		bot (ChatGPT) : an instance of the ChatGPT class from the Wrapper API
		rubric_mode (str) : flag to indicate either providing the full rubric,
			or only the rubric items relevant to the current question
		full_rubric (str) : the rubric context, read from grading_rubric.txt
		start_index (int) : the index of the first row of data to send
		end_index (int) : the index of the last row of data to send (exclusive)

	kwargs:
		output_name (str) : the name of the output file. If not specified,
			the default name is chatgpt_labels_<start_index>_<end_index>.csv

	returns:
		boolean - an indicator of whether a checkpoint CSV file
			was successfully generated. If this is False, you have reached
			the request limit by ChatGPT.
	"""
	responses = []
	df_subset = df.loc[start_index : min(len(df), end_index), :].reset_index()

	for i, row in df_subset.iterrows():
		if rubric_mode == 'full':
			query = build_chatgpt_prompt_full_rubric(row, full_rubric)
		else:
			query = build_chatgpt_prompt_individual_rubric(row)

		success, response, message = bot.ask(query)
		if success:
			responses.append(response)
		else:
			print("Error at line", start_index + i, "with message", message)
			responses.append("")
			if len(responses) == 1:
				return False
		time.sleep(0.5)

	df_subset["ChatGPT Label"] = responses

	if output_name is None:
		output_name = f"chatgpt_labels_{start_index:04d}_{end_index:04d}.csv"
	df_subset.to_csv(os.path.join(output_dir, output_name), index = False)
	print(f"Finished querying chatgpt from row {start_index} to {end_index}")
	return True


def get_remaining_labels(bot, rubric_mode, full_rubric):
	"""
	Gather all the rows with missing labels in the saved checkpoint files (due to the message cap),
	then run another set of ChatGPT queries to collect labels for these rows
	"""
	df_checkpoints = [
	    pd.read_csv(os.path.join(output_dir, filename))
	    for filename in os.listdir(output_dir)
	]
	df_combined = pd.concat(df_checkpoints).drop_duplicates(subset = ["Index"])
	df_remaining = df_combined \
		.loc[pd.isna(df_combined["ChatGPT Label"]), :] \
		.drop(columns = ['index']) \
		.reset_index()

	assert query_response(
		df_remaining, bot, rubric_mode, full_rubric,
		0, len(df_remaining), "chatgpt_remaining_labels.csv"
	), "Error while collecting the remaining labels, maybe exceeded the hourly request limit"
	return df_combined


def generate_final_output(df_combined, rubric_mode):
	df_remaining = pd.read_csv(os.path.join(output_dir, "chatgpt_remaining_labels.csv"))
	df_final = df_combined.merge(df_remaining[["Index", "ChatGPT Label"]], how = "left", on = ["Index"])
	df_final["ChatGPT Label"] = np.where(
		pd.isna(df_final["ChatGPT Label_x"]),
		df_final["ChatGPT Label_y"],
		dfm["ChatGPT Label_x"]
	)
	df_final \
		.dropna(subset = ["ChatGPT Label"]).drop(columns = ["index", "ChatGPT Label_x", "ChatGPT Label_y"])
		.rename(columns = {"ChatGPT Label" : "ChatGPT Response"}) \
		.to_csv(os.path.join(output_dir, "chatgpt_labels.csv"), index = False)


def main(starting_page, rubric_mode, n_rows_per_page = 100):
	"""
	Use the ChatGPT wrapper to send queries to ChatGPT and
	record its responses to a new csv file called chatgpt_labels.csv

	args:
		starting_page (int) : the index of the starting page, with each page
			containing n_rows_per_page rows. For example if starting_page = 5,
			the first 5*n_rows_per_page rows in the input dataframe are skipped

		rubric_mode (str) : flag to indicate either providing the full rubric,
			or only the rubric items relevant to the current question

		n_rows_per_page (int) : the number of rows (responses) to collect in a page
	"""
	df_input = pd.read_csv("SE_OE_Coding_Merged.csv").sample(frac = 1, random_state = 0)
	df_rubric = pd.read_csv("grading_rubric.csv")
	df_input["Question Type"] = df_input.apply(get_question_type, axis = 1)
	df_input = df_input.merge(df_rubric)

	full_rubric = convert_full_rubric_to_text(df_rubric)
	bot = ChatGPT()

	for start in range(starting_page*n_rows_per_page, len(df_input), n_rows_per_page):
		success = query_response(df_input, bot, rubric_mode, full_rubric, start, start + n_rows_per_page)

		# when the message cap has been reached, wait for a bit more than 1 hour
		# then repeat the previous request
		if not success:
			print("Message cap reached. Waiting for 4000s ...")
			time.sleep(4000)
			print("Waiting finished. Now attempting to repeat the previous request")
			bot = ChatGPT()
			assert query_response(df_input, bot, rubric_mode, full_rubric, start, start + n_rows_per_page)

	df_combined = get_remaining_labels(bot, rubric_mode, full_rubric)
	generate_final_output(df_combined, rubric_mode)


if __name__ == '__main__':
	rubric_mode = sys.argv[1]
	starting_page = int(sys.argv[2]) if len(sys.argv) > 2 else 0

	assert rubric_mode in ['full', 'individual'], \
		"the rubric_mode parameter should be 'full' or 'individual'"

	if rubric_mode == "full" and not os.path.exists("output_full_rubric"):
		os.mkdir("output_full_rubric")
	if rubric_mode == "individual" and not os.path.exists("output_individual_rubric"):
		os.mkdir("output_individual_rubric")

	output_dir = "output_full_rubric" if rubric_mode == "full" else "output_individual_rubric"
	main(starting_page, rubric_mode)
