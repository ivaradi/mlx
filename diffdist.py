# Program to create a diff of two distribution directories

#--------------------------------------------------------------------------

from mlx.update import manifestName, Manifest

import tarfile
import sys
import os
import tempfile

#--------------------------------------------------------------------------

tarName = "diffdist.tar.bz2"

#--------------------------------------------------------------------------

def usage():
    """Print a usage message."""
    print "Usage: %s <old dist dir> <new dist dir>" % (sys.argv[0],)

#--------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv)!=3:
        usage()
        sys.exit(1)

    oldDirectory = sys.argv[1]
    newDirectory = sys.argv[2]
    
    oldManifest = Manifest()
    newManifest = Manifest()

    with open(os.path.join(oldDirectory, manifestName), "rt") as f:
        oldManifest.readFrom(f)
        
    with open(os.path.join(newDirectory, manifestName), "rt") as f:
        newManifest.readFrom(f)

    finalManifest = newManifest.copy()
        
    (modifiedAndNew, removed) = oldManifest.compare(newManifest)
    #print removed
    #print modifiedAndNew

    tarFile = tarfile.open(tarName, mode="w:bz2")
    
    for (path, newSize, newSum) in modifiedAndNew:
        copyOld = False
        if path in oldManifest:
            (oldSize, oldSum) = oldManifest[path]
            if path.endswith(".pyc") and newSize<1024 and newSize==oldSize:
                with open(os.path.join(oldDirectory, path), "rb") as f:
                    oldData = f.read()
                with open(os.path.join(newDirectory, path), "rb") as f:
                    newData = f.read()
                    
                numDiffs = 0
                for i in range(0, newSize):
                    if oldData[i]!=newData[i]: numDiffs += 1

                if numDiffs<=3:
                    print "File %s is considered to be the same in both versions with %d changes" % \
                          (path, numDiffs)
                    finalManifest.addFile(path, oldSize, oldSum)
                    copyOld = True
                    

        if not copyOld:
            print ">>> File %s is being copied" % (path,)
            tarFile.add(os.path.join(newDirectory, path), arcname = path)
            
    (fd, path) = tempfile.mkstemp()
    with os.fdopen(fd, "wt") as f:
        finalManifest.writeInto(f)
    os.chmod(path, 0644)
    tarFile.add(path, arcname = manifestName)
    tarFile.close()

    os.remove(path)

    print
    print "%s created" % (tarName,)
    if removed:
        print
        print "Files to remove:"
        print
        for path in removed:
            print "  ", path
