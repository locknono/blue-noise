"""
The algorithm could speed up by memorizing some calculating results
"""

from scipy import stats
import numpy as np
import random
import math
import logging


def getDistance(p1, p2):
    x1, y1, x2, y2 = p1['lat'], p1['lng'], p2['lat'], p2['lng']
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))


def getOverlapDict(points):
    overlapDict = {}
    for p in points:
        coor = (p['lat'], p['lng'])
        if coor not in overlapDict:
            overlapDict[coor] = [{"id": p['id'], "lat": p['lat'], "lng": p['lng']}]
        else:
            overlapDict[coor].append({"id": p['id'], "lat": p['lat'], "lng": p['lng']})
    for k in overlapDict:
        for points in overlapDict[k]:
            if len(points) == 1:
                overlapDict.pop(k)
    return overlapDict


def dereplication(points):
    # should i check for overlap condition here?
    # if overlap exists,a 3-dimension blue noise algorithm is required?
    pointsSet = []
    pSet = set()
    for p in points:
        if (p['lat'], p['lng']) in pSet:
            pass
        else:
            pSet.add((p['lat'], p['lng']))
            pointsSet.append(p)
    return pointsSet


def getGeoDistance(p1, p2):
    # result matches `leaflet` coordinate system
    # can not memorize the distance maxtrix because it's too large,too space-consuming
    lon1 = p1['lng']
    lon2 = p2['lng']
    lat1 = p1['lat']
    lat2 = p2['lat']
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371
    dis = c * r * 1000
    return dis


def getdiskR(point, r, kde):
    radius = r / kde([point['lat'], point['lng']])[0]
    point['r'] = radius
    return radius


def setdiskRForAllPoints(points, r, kde):
    for p in points:
        p['r'] = getdiskR(p, r, kde)


# could speed up by selecting points in `unSampledPoints` List
def getAllPointsBetweenRAnd2R(center, r, points):
    allPoints = []
    for p in points:
        distance = getGeoDistance(center, p)
        if (distance > r and distance < 2 * r):
            allPoints.append(p)
    return allPoints


def ifAllPointsAreInactive(points):
    for p in points:
        if p['status'] == 1 or p['status'] == None:
            return False
    return True


def setSamplePointsToOutputFormat(points, samplePoints):
    for p in points:
        del p['status']
        del p['coverByDisk']
    for p1 in samplePoints:
        p1['pointsInDisk'] = []
        for p2 in points:
            if p1 == p2:
                continue
            if getGeoDistance(p1, p2) < p1['r']:
                p1['pointsInDisk'].append(p2)
    for p in points:
        if 'pointsInDisk' in p:
            for pInDisk in p['pointsInDisk']:
                if 'r' in pInDisk:
                    del pInDisk['r']
    return samplePoints


def ifAllPointsInDisk(points, samplePoints):
    for p in points:
        if p['coverByDisk'] == False:
            return False
    return True


# if `points` list is lat-lng ordered,shuffle first.
def getRandomPoint(points, samplePoints, kde, r):
    if (len(samplePoints) == 0):
        return points[random.randint(0, len(points) - 1)]
    for p in points:
        if p['status'] == 0 or p['status'] == 1:
            continue
        if p['coverByDisk'] == True:
            continue
        radius = p['r'] if 'r' in p else getdiskR(p, r, kde)
        for sp in samplePoints:
            dis = getGeoDistance(p, sp)
            if dis < sp['r'] or dis < radius:
                break
        else:
            return p
    return None


"""
@:param originalPoints: {id:string,lat:float,lng:float}[]
@:param r and the disk radius are positively correlated
"""


def blueNoise(originalPoints, r):
    activePoints = []
    samplePoints = []
    allLat = []
    allLng = []
    points = dereplication(originalPoints)
    overlapDict = getOverlapDict(originalPoints)
    overlapRate = round((len(originalPoints) - len(points)) / len(originalPoints), 2)
    logging.info('original points:' + str(len(originalPoints)))
    logging.info('overlap rate:' + str(overlapRate))
    logging.info('blue noise for ' + str(len(points)) + ' points')
    for p in points:
        allLat.append(p['lat'])
        allLng.append(p['lng'])
    dataForKDE = np.vstack([allLat, allLng])
    kde = stats.gaussian_kde(dataForKDE)

    # @status: 0 for inactive,1 for active,None for neither active nor inactive
    # if a point is inactive,then its points between R and 2R must are all covered by disks
    # but `a point is covered by disk` does not mean it is inactive

    for p in points:
        p['status'] = None
        p['coverByDisk'] = False

    initialActivePoint = getRandomPoint(points, samplePoints, kde, r)
    initialActivePoint['status'] = 1
    initialActivePoint['coverByDisk'] = True
    samplePoints.append(initialActivePoint)
    activePoints.append(initialActivePoint)

    while (len(activePoints) > 0 or ifAllPointsInDisk(points, samplePoints) == False):
        if len(activePoints) == 0:
            initialActivePoint = getRandomPoint(points, samplePoints, kde, r)
            if initialActivePoint == None:
                break
            initialActivePoint['status'] = 1
            initialActivePoint['coverByDisk'] = True
            samplePoints.append(initialActivePoint)
            logging.info('sampling points:{0}'.format(len(samplePoints)))
            activePoints.append(initialActivePoint)
        randomActivePoint = activePoints[random.randint(
            0, len(activePoints) - 1)]
        diskR = randomActivePoint['r'] if 'r' in randomActivePoint else getdiskR(
            randomActivePoint, r, kde)
        pointsBetweenRand2R = getAllPointsBetweenRAnd2R(
            randomActivePoint, diskR, points)
        for p1 in pointsBetweenRand2R:
            if p1['status'] == 1 or p1['status'] == 0:
                continue
            if p1['coverByDisk'] == True:
                continue
            diskRForP1 = p1['r'] if 'r' in p1 else getdiskR(p1, r, kde)
            for p2 in samplePoints:
                diskRForP2 = p2['r']
                distance = getGeoDistance(p1, p2)
                if distance <= diskRForP2:
                    p1['coverByDisk'] = True
                    break
                if distance <= diskRForP1:
                    break
            else:
                p1['status'] = 1
                p1['coverByDisk'] = True
                activePoints.append(p1)
                samplePoints.append(p1)
                logging.info('sampling points:{0}'.format(len(samplePoints)))
                break
        else:
            randomActivePoint['status'] = 0
            activePoints.remove(randomActivePoint)
    setSamplePointsToOutputFormat(points, samplePoints)

    if (len(overlapDict.keys()) > 0):
        for p in samplePoints:
            for i in range(len(p['pointsInDisk']) - 1, 0, -1):
                coord = (p['pointsInDisk'][i]['lat'], p['pointsInDisk'][i]['lng'])
                overlapPoints = overlapDict[coord]
                for overlapPoint in overlapPoints:
                    if p['pointsInDisk'][i]['id'] != overlapPoint['id']:
                        p['pointsInDisk'].append(overlapPoint)
            coord = (p['lat'], p['lng'])
            overlapPoints = overlapDict[coord]
            for overlapPoint in overlapPoints:
                if overlapPoint['id'] != p['id']:
                    p['pointsInDisk'].append(overlapPoint)
    return samplePoints


if __name__ == '__main__':
    pass
