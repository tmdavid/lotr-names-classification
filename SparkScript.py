import sys 

from pyspark import SparkConf, SparkContext
from pyspark.ml import Pipeline
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import NGram
from pyspark.ml.feature import IDF
from pyspark.ml.feature import HashingTF
from pyspark.ml.classification import NaiveBayes
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.mllib.evaluation import MulticlassMetrics
from pyspark.sql import Row
from pyspark.sql import SQLContext


# TODO: send the master address via command line argument
conf = SparkConf().setMaster(sys.argv[1]).setAppName(
    "LOTR Names classification")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)

# TODO: send the file location via command line argument
# Import both the train and test dataset and register them as tables
imported_data = sqlContext.read.format('com.databricks.spark.csv').options(
    header='true') \
    .load(sys.argv[2])

# Map the race to a number
race_to_number = {'Man': 0.0, 'Elf': 1.0, 'Hobbit': 2.0, 'Dwarf': 3.0}

# Build a new rdd made of a row that has the name of the character, the name as a list of the characters, the race of
# the character
data_rdd = imported_data.map(lambda row: Row(complete_name=row.name, name=list(row.name.lower()),
                                             race=race_to_number[row.race]))
                                             
df = sqlContext.createDataFrame(data_rdd)

# Pipeline consisting of two stages: NGrams and HashingTF
ngram = NGram(n=3, inputCol="name", outputCol="nGrams")
hashingTF = HashingTF(numFeatures=500, inputCol="nGrams", outputCol="TF")
pipeline = Pipeline(stages=[ngram, hashingTF])

# Fit the pipeline 
pipelined_data = pipeline.fit(df)
transformed_data = pipelined_data.transform(df)
training_set, test_set = transformed_data.randomSplit([0.8, 0.2], seed=10)

# Create the model, train and predict
nb = NaiveBayes(smoothing=1.0, modelType="multinomial", featuresCol='TF', labelCol='race')
training_set.cache()
model = nb.fit(training_set)
predictions = model.transform(test_set)

# Evaluate the results
evaluator = MulticlassClassificationEvaluator(predictionCol='prediction', labelCol='race')
result = predictions.select('race','prediction')
result_rdd = result.rdd
metrics = MulticlassMetrics(result_rdd)

print("Naive Bayes model evaluation")
print("F score: {}".format(evaluator.evaluate(result)))
print(metrics.confusionMatrix())
for k,v in race_to_number.iteritems():
    print("F score for {}: {}".format(k, metrics.fMeasure(v)))
print("Precision: {}".format(evaluator.evaluate(result, {evaluator.metricName: 'precision'})))
print ("Contigency table of the prediction results of naive bayes model")
result.stat.crosstab('prediction', 'prediction').show()

print("Predictions for naive bayes: {}".format(predictions.select('complete_name', 'prediction').collect()))
