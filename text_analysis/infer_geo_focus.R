# List of required packages
packages <- c("newsmap", "quanteda", "dplyr", "countrycode", "jsonlite")

# Function to check and install missing packages
install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg)
  }
}

# Apply the function to each package
lapply(packages, install_if_missing)

# Load the libraries after installation
lapply(packages, library, character.only = TRUE)


infer_geo_focus <- function(file = "main_texts_for_geo_focus_inference.txt") {
  # Convert articles to a dataframe
  df <- data.frame(text = readLines(file))

  # Create corpus
  corp <- corpus(df, text_field = "text")

  # Tokenize
  toks <- tokens(corp,
    remove_punct = TRUE,
    remove_numbers = TRUE, remove_symbols = TRUE
  )
  toks <- tokens_remove(toks, stopwords("german"),
    valuetype = "fixed", padding = TRUE
  )

  # Apply dictionary
  toks_label <- tokens_lookup(toks,
    newsmap::data_dictionary_newsmap_de,
    levels = 3
  )
  dfmt_label <- dfm(toks_label)

  # Create feature dfm
  dfmt_feat <- dfm(toks, tolower = FALSE)
  dfmt_feat <- dfm_select(dfmt_feat, "^[A-ZÄÖÜ][A-Za-zäöüß1-2]+",
    valuetype = "regex", case_insensitive = FALSE
  )
  dfmt_feat <- dfm_trim(dfmt_feat, min_termfreq = 10)

  # Create and apply model
  model <- textmodel_newsmap(dfmt_feat, dfmt_label)
  pred <- predict(model)
  pred <- as.character(pred)

  # Convert to full country names
  country_names <- countrycode(pred, "iso2c", "country.name")

  return(country_names)
}

country_names <- infer_geo_focus("main_texts_for_geo_focus_inference.txt")
# delete the file
file.remove("main_texts_for_geo_focus_inference.txt")

# write to a .txt file
write.table(country_names, "geo_inference_country_names.txt",
  row.names = FALSE, quote = FALSE, col.names = FALSE
)
