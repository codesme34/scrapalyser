import scrapalyser

# Simple scan (returns dict)
report = scrapalyser.scan("https://example.com")
print(report)

# With all options
report = scrapalyser.scan(
    url="https://example.com",
    output="txt",
    lang="fr",
    save="report.txt",
)
