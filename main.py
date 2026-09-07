from collectors.ipindia import IPIndiaCollector

collector = IPIndiaCollector()

html = collector.get_patent_details("202641091331")

with open(
    "data/raw/patent_202641091331.html",
    "w",
    encoding="utf-8"
) as f:
    f.write(html)

print("Saved:", len(html), "characters")