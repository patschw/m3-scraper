library(jsonlite)
install.packages("newsmap")
library(newsmap)
install.packages("quanteda")
library(quanteda)

# Read input from stdin
# Start of Selection
input_data <- fromJSON("archive_articles.json")
# End of Selection
# Start of Selection
articles <- data.frame(
  url = input_data$url,
  main_text = input_data$main_text,
  stringsAsFactors = FALSE
)
# End of Selection
# End of Selection

# Create a corpus from the articles
# Start of Selection
corp <- corpus(articles, text_field = "main_text")

# Tokenize the corpus
toks <- tokens(corp, remove_punct = TRUE, remove_numbers = TRUE, remove_symbols = TRUE)

# Create a dfm (document-feature matrix)
dfmat <- dfm(toks)

# Load the pre-trained German newsmap model
# Note: You may need to adjust the path to where you've saved the model
data(data_dictionary_newsmap_de)

# Apply the newsmap model
result <- newsmap(dfmat, data_dictionary_newsmap_german)

# Get the top predicted country for each document
top_countries <- apply(result, 1, function(x) names(which.max(x)))

# Create a data frame with document IDs and top countries
output <- data.frame(
  doc_id = docnames(dfmat),
  country = top_countries,
  stringsAsFactors = FALSE
)

# Convert country codes to country names (optional)
# You might want to create a mapping of country codes to full names
country_names <- c(
  "DE" = "Germany",
  "AT" = "Austria",
  "CH" = "Switzerland",
  # Add more mappings as needed
)
output$country <- country_names[output$country]

# Output results as JSON
cat(toJSON(output$country))
