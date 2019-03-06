from blue_noise import blueNoise
import time
import csv
import json
from itertools import islice
import logging

if __name__ == '__main__':
    for r in [100000, 25000, 6000, 1250, 300]:
        t1 = time.time()
        points = []
        with open('./testData.csv', 'r', encoding='utf-8') as f:
            csvF = csv.reader(f)
            for row in islice(csvF, 1, None):
                pID = row[0]
                lat = float(row[1])
                lng = float(row[2])
                points.append({'id': pID, 'lat': lat, 'lng': lng})

        samplePoints = blueNoise(points, r)

        recentBlueNoiseFilePath = './samplePoints-{0}-{1}-{2}.json'.format(r, len(samplePoints),
                                                                           len(samplePoints) / len(
                                                                               points))
        with open(recentBlueNoiseFilePath, 'w',
                  encoding='utf-8') as f:
            logging.info(str(r) + ' sampling over,' + str((time.time() - t1) / 60))
            logging.info('-------------------')
            f.write(json.dumps(samplePoints))
