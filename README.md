# Auswertungstool

## USAGE

The brackets around the arguments, e.g. `<option>`, are only in this documentation to indicate the argument you set yourself, do not actually write the brackets around the options you set.

### create diagram:

```
python3 main.py plot <yourCsvFile.csv> <xAxisId> <yAxisId>
```

### create filtered csv:

```
python3 main.py filter <yourCsvFile.csv>
```

### create word cloud:

```
python3 main.py word_cloud <yourCsvFile.csv> <questionId>
```