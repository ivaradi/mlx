
from .config import Config
from .util import utf2unicode

import os
import sys
import urllib.request, urllib.error, urllib.parse
import tempfile
import socket
import subprocess
import hashlib
import traceback
import io

if os.name=="nt":
    import win32api

#------------------------------------------------------------------------------

## @package mlx.update
#
# Automatic update handling.
#
# The program can update itself automatically. For this purpose it maintains a
# manifest of the files installed containing the relative paths, sizes and
# checksums of each files. When the program starts up, this manifest file is
# downloaded from the update server and is compared to the local one. Then the
# updated and new files are downloaded with names that are created by appending
# the checksum to the actual name, so as not to overwrite any existing files at
# this stage. If all files are downloaded, the downloaded files are renamed to
# their real names. On Windows, the old file is removed first to avoid trouble
# with 'busy' files. If removing a file fails, the file will be moved to a
# temporary directory, that will be removed when the program starts the next
# time.

#------------------------------------------------------------------------------

manifestName = "MLXMANIFEST"
toremoveName = "toremove"

#------------------------------------------------------------------------------

class Manifest(object):
    """The manifest of the files.

    The manifest file consists of one line for each file. Each line contains 3
    items separated by tabs:
    - the path of the file relative to the distribution's root
    - the size of the file
    - the MD5 sum of the file."""
    def __init__(self):
        """Construct the manifest."""
        self._files = {}

    @property
    def files(self):
        """Get an iterator over the files.

        Each file is returned as a 3-tuple with items as in the file."""
        for (path, (size, sum)) in self._files.items():
            yield (path, size, sum)

    def copy(self):
        """Create a copy of the manifest."""
        manifest = Manifest()
        manifest._files = self._files.copy()
        return manifest
        
    def addFile(self, path, size, sum):
        """Add a file to the manifest."""
        self._files[path] = (size, sum)

    def addFiles(self, baseDirectory, subdirectory):
        """Add the files in the given directory and subdirectories of it to the
        manifest."""
        directory = baseDirectory
        for d in subdirectory: directory = os.path.join(directory, d)
        
        for entry in os.listdir(directory):
            fullPath = os.path.join(directory, entry)
            if os.path.isfile(fullPath):
                size = os.stat(fullPath).st_size
                sum = hashlib.md5()
                with open(fullPath, "rb") as f:
                    while True:
                        data = f.read(4096)
                        if data: sum.update(data)
                        else: break
                self.addFile("/".join(subdirectory + [entry]), size,
                             sum.hexdigest())
            elif os.path.isdir(fullPath):
                self.addFiles(baseDirectory, subdirectory + [entry])
                
    def readFrom(self, file):
        """Read a manifest from the given file object."""
        for line in iter(file.readline, ""):
            (path, size, sum) = line.strip().split("\t")
            self._files[path] = (int(size), sum)

    def writeInto(self, file):
        """Write the manifest into the file at the given path."""
        for (path, (size, sum)) in self._files.items():
            file.write("%s\t%d\t%s\n" % (path, size, sum))

    def compare(self, other):
        """Compare this manifest with the other one.

        This returns a tuple of two lists:
        - the files that are either different or are present in other, but not
        here. Each file is returned as a 3-tuple as with other functions, the
        size and sum are those of the new file.
        - the paths of the files that are present here, but not in other."""
        modifiedAndNew = []
        for (path, otherSize, otherSum) in other.files:
            if path in self._files:
                (size, sum) = self._files[path]
                if size!=otherSize or sum!=otherSum:
                    modifiedAndNew.append((path, otherSize, otherSum))
            else:
                modifiedAndNew.append((path, otherSize, otherSum))

        if os.name=="nt":
            otherFiles = [path.lower() for path in other._files]
        else:
            otherFiles = other._files

        removed = [path for path in self._files if
                   (path.lower() if os.name=="nt" else path) not in otherFiles]
        
        return (modifiedAndNew, removed)

    def __contains__(self, path):
        """Determine if the given path is in the manifest."""
        return path in self._files

    def __getitem__(self, path):
        """Get data of the file with the given path."""
        return self._files[path] if path in self._files else None
            
#------------------------------------------------------------------------------

class ClientListener(object):
    """A listener that sends any requests via a socket."""
    def __init__(self, sock):
        """Construct the listener."""
        self._sock = sock

    def downloadingManifest(self):
        """Called when the downloading of the manifest has started."""
        self._send(["downloadingManifest"])

    def downloadedManifest(self):
        """Called when the manifest has been downloaded."""
        self._send(["downloadedManifest"])

    def needSudo(self):
        """Called when an admin-level program must be called to complete the
        update.

        This is not valid from a client, as that client is supposed to be the
        admin-level program :)"""
        assert False

    def setTotalSize(self, numToModifyAndNew, totalSize, numToRemove,
                     numToRemoveLocal):
        """Called when starting the downloading of the files."""
        self._send(["setTotalSize", str(numToModifyAndNew), str(totalSize),
                    str(numToRemove), str(numToRemoveLocal)])

    def setDownloaded(self, downloaded):
        """Called periodically after downloading a certain amount of data."""
        self._send(["setDownloaded", str(downloaded)])

    def startRenaming(self):
        """Called when the renaming of the downloaded files is started."""
        self._send(["startRenaming"])

    def renamed(self, path, count):
        """Called when a file has been renamed."""
        self._send(["renamed", path, str(count)])

    def startRemoving(self):
        """Called when the removing of files has started."""
        self._send(["startRemoving"])

    def removed(self, path, count):
        """Called when a file has been removed."""
        self._send(["removed", path, str(count)])

    def writingManifest(self):
        """Called when we have started writing the manifest."""
        self._send(["writingManifest"])

    def done(self):
        """Called when the update has completed."""
        self._send(["done"])

    def failed(self, what):
        """Called when something has failed."""
        self._send(["failed", what])

    def _send(self, words):
        """Send the given words via the socket."""
        self._sock.send(bytes("\t".join(words) + "\n", "utf-8"))

#------------------------------------------------------------------------------

def readLocalManifest(directory):
    """Read the local manifest from the given directory."""
    manifestPath = os.path.join(directory, manifestName)

    manifest = Manifest()
    try:
        with open(manifestPath, "rt") as f:
            manifest.readFrom(f)
    except Exception as e:
        print("Error reading the manifest, ignoring:", utf2unicode(str(e)))
        manifest = Manifest()

    return manifest

#------------------------------------------------------------------------------

def prepareUpdate(directory, updateURL, listener):
    """Prepare the update by downloading the manifest and comparing it with the
    local one."""
    manifest = readLocalManifest(directory)
        
    updateURL += "/" + os.name

    listener.downloadingManifest()
    f = None
    try:
        updateManifest = Manifest()
        reply = urllib.request.urlopen(updateURL + "/" + manifestName)
        charset = reply.headers.get_content_charset()
        content = reply.read().decode("utf-8" if charset is None else charset)
        updateManifest.readFrom(io.StringIO(content))

    except Exception as e:
        error = utf2unicode(str(e))
        print("Error downloading manifest:", error, file=sys.stderr)
        listener.failed(error)
        return None
    finally:
        if f is not None: f.close()

    listener.downloadedManifest()

    (modifiedAndNew, removed) = manifest.compare(updateManifest)

    return (manifest, updateManifest, modifiedAndNew, removed)

#------------------------------------------------------------------------------

def getToremoveFiles(directory):
    """Add the files to remove from the toremove directory."""
    toremove = []
    toremoveDirectory = os.path.join(directory, toremoveName)
    if os.path.isdir(toremoveDirectory):
        for entry in os.listdir(toremoveDirectory):
            toremove.append(os.path.join(toremoveName, entry))
    return toremove

#------------------------------------------------------------------------------

def createLocalPath(directory, path):
    """Create a local path from the given manifest path."""
    localPath = directory
    for element in path.split("/"):
        localPath = os.path.join(localPath, element)
    return localPath

#------------------------------------------------------------------------------

def getToremoveDir(toremoveDir, directory):
    """Get the path of the directory that will contain the files that are to be
    removed."""
    if toremoveDir is None:
        toremoveDir = os.path.join(directory, toremoveName)
        try:
            os.mkdir(toremoveDir)
        except:
            pass

    return toremoveDir

#------------------------------------------------------------------------------

def removeFile(toremoveDir, directory, path):
    """Remove the file at the given path or store it in a temporary directory.

    If the removal of the file fails, it will be stored in a temporary
    directory. This is useful for files thay may be open and cannot be removed
    right away."""
    try:
        os.remove(path)
    except:
        try:
            sum = hashlib.md5()
            sum.update(bytes(path, "utf-8"))
            toremoveDir = getToremoveDir(toremoveDir, directory)
            targetPath = os.path.join(toremoveDir, sum.hexdigest())
            try:
                os.remove(targetPath)
            except:
                pass
            os.rename(path, targetPath)
        except Exception as e:
            print("Cannot remove file " + path + ": " + utf2unicode(str(e)))

#------------------------------------------------------------------------------

def removeFiles(directory, listener, removed, count):
    """Remove the given files."""
    toremoveDir = None
    
    listener.startRemoving()

    removed.sort(reverse = True)
    for path in removed:
        removePath = createLocalPath(directory, path)
        removeFile(toremoveDir, directory, removePath)

        removeDirectory = os.path.dirname(removePath)
        try:
            os.removedirs(removeDirectory)
        except:
            pass

        count += 1
        listener.removed(path, count)

    return count

#------------------------------------------------------------------------------

def updateFiles(directory, updateURL, listener,
                manifest, modifiedAndNew, removed, localRemoved):
    """Update the files according to the given information."""
    totalSize = 0
    for (path, size, sum) in modifiedAndNew:
        totalSize += size

    listener.setTotalSize(len(modifiedAndNew), totalSize,
                          len(removed), len(localRemoved))

    downloaded = 0
    fin = None
    toremoveDir = None

    try:        
        updateURL += "/" + os.name

        removeCount = 0
        if localRemoved:
            removeCount = removeFiles(directory, listener,
                                      localRemoved, removeCount)
        
        for (path, size, sum) in modifiedAndNew:
            targetFile = createLocalPath(directory, path)
            targetFile += "."
            targetFile += sum

            targetDirectory = os.path.dirname(targetFile)
            if not os.path.isdir(targetDirectory):
                os.makedirs(targetDirectory)
                
            with open(targetFile, "wb") as fout:
                fin = urllib.request.urlopen(updateURL + "/" + path)
                while True:
                    data = fin.read(4096)
                    if not data:
                        break
                    fout.write(data)
                    downloaded += len(data)
                    listener.setDownloaded(downloaded)
                fin.close()
                fin = None
                
        listener.startRenaming()
        count = 0
        for (path, size, sum) in modifiedAndNew:
            targetFile = createLocalPath(directory, path)

            downloadedFile = targetFile + "." + sum
            if os.name=="nt" and os.path.isfile(targetFile):
                removeFile(toremoveDir, directory, targetFile)
            os.rename(downloadedFile, targetFile)
            count += 1
            listener.renamed(path, count)

        removeFiles(directory, listener, removed, removeCount)

        listener.writingManifest()

        manifestPath = os.path.join(directory, manifestName)
        with open(manifestPath, "wt") as f:
            manifest.writeInto(f)
        
        listener.done()
    except Exception as e:
        exc = traceback.format_exc()
        print(utf2unicode(exc), file=sys.stderr)
        
        error = utf2unicode(str(e))
        print("Error:", error, file=sys.stderr)

        listener.failed(error)

#------------------------------------------------------------------------------

def isDirectoryWritable(directory):
    """Determine if the given directory can be written."""
    checkFile = os.path.join(directory, "writable.chk")
    try:
        f = open(checkFile, "wt")
        f.close()
        return True
    except Exception as e:
        return False
    finally:
        try:
            os.remove(checkFile)
        except:
            pass

#------------------------------------------------------------------------------

def processMLXUpdate(buffer, listener):
    """Process the given buffer supposedly containing a list of commands."""
    endsWithLine = buffer[-1]=="\n"
    lines = buffer.splitlines()

    if endsWithLine:
        buffer = ""
    else:
        buffer = lines[-1]
        lines = lines[:-1]
        
    for line in lines:
        words = line.split("\t")
        try:
            command = words[0]
            if command=="downloadingManifest":
                listener.downloadingManifest()
            elif command=="downloadedManifest":
                listener.downloadedManifest()
            elif command=="setTotalSize":
                listener.setTotalSize(int(words[1]), int(words[2]),
                                      int(words[3]), int(words[4]))
            elif command=="setDownloaded":
                listener.setDownloaded(int(words[1]))
            elif command=="startRenaming":
                listener.startRenaming()
            elif command=="renamed":
                listener.renamed(words[1], int(words[2]))
            elif command=="startRemoving":
                listener.startRemoving()
            elif command=="removed":
                listener.removed(words[1], int(words[2]))
            elif command=="writingManifest":
                listener.writingManifest()
            elif command=="done":
                listener.done()
            elif command=="failed":
                listener.failed(words[1])
        except Exception as e:
            print("Failed to parse line '%s': %s" % \
                  (line, utf2unicode(str(e))), file=sys.stderr)

    return buffer

#------------------------------------------------------------------------------

def sudoUpdate(directory, updateURL, listener, manifest):
    """Perform the update via the mlxupdate program."""
    manifestFD = None
    manifestFile = None
    serverSocket = None
    mlxUpdateSocket = None
    try:
        (manifestFD, manifestFile) = tempfile.mkstemp()
        f = os.fdopen(manifestFD, "wt")
        try:
            manifest.writeInto(f)
        finally:
            f.close()            
            manifestFD = None

        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serverSocket.bind(("127.0.0.1", 0))
        (_host, port) = serverSocket.getsockname()
        serverSocket.listen(1)


        if os.name=="nt":
            win32api.ShellExecute(0, "open", os.path.join(directory, "mlxupdate"),
                                  str(port) + " " +  manifestFile + " " + updateURL, "", 1)
        else:
            process = subprocess.Popen([os.path.join(directory, "mlxupdate"),
                                        str(port), manifestFile, updateURL],
                                        shell = os.name=="nt")

        (mlxUpdateSocket, _) = serverSocket.accept()
        serverSocket.close()
        serverSocket = None
    
        buffer = ""
        while True:
            data = mlxUpdateSocket.recv(4096)
            if not data:
                break;

            buffer += str(data, "utf-8")
            buffer = processMLXUpdate(buffer, listener)

        mlxUpdateSocket.close()
        mlxUpdateSocket = None

        if os.name!="nt":
            process.wait()
        
    except Exception as e:
        error = utf2unicode(str(e))
        print("Failed updating:", error, file=sys.stderr)
        listener.failed(error)
    finally:
        if serverSocket is not None:
            try:
                serverSocket.close()
            except:
                pass
        if mlxUpdateSocket is not None:
            try:
                mlxUpdateSocket.close()
            except:
                pass
        if manifestFD is not None:
            try:
                os.close(manifestFD)
            except:
                pass
        if manifestFile is not None:
            try:
                os.remove(manifestFile)
            except:
                pass
        

#------------------------------------------------------------------------------

def update(directory, updateURL, listener, fromGUI = False):
    """Perform the update."""
    try:
        result = prepareUpdate(directory, updateURL, listener)
        if result is None:
            return

        (manifest, updateManifest, modifiedAndNew, removed) = result        
        localRemoved = getToremoveFiles(directory)

        if not modifiedAndNew and not removed and not localRemoved:
            listener.done()
            return

        if fromGUI and not isDirectoryWritable(directory):
            if listener.needSudo():
                sudoUpdate(directory, updateURL, listener, updateManifest)
        else:
            updateFiles(directory, updateURL, listener, updateManifest,
                        modifiedAndNew, removed, localRemoved)
    except Exception as e:
        exc = traceback.format_exc()
        print(utf2unicode(exc), file=sys.stderr)
        
        error = utf2unicode(str(e))
        print("Update error:", error, file=sys.stderr)
        
        listener.failed(error)

#------------------------------------------------------------------------------

def updateProcess():
    """This is called in the child process, when we need a child process."""
    try:
        clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    
        clientSocket.connect(("127.0.0.1", int(sys.argv[1])))

        directory = os.path.dirname(sys.argv[0])

        manifest = readLocalManifest(directory)

        updateManifest = Manifest()
        with open(sys.argv[2], "rt") as f:
            updateManifest.readFrom(f)

        (modifiedAndNew, removed) = manifest.compare(updateManifest)
        localRemoved = getToremoveFiles(directory)

        updateFiles(directory, sys.argv[3],
                    ClientListener(clientSocket),
                    updateManifest, modifiedAndNew, removed, localRemoved)
    except:
        exc = traceback.format_exc()
        print(utf2unicode(exc), file=sys.stderr)

#------------------------------------------------------------------------------

def buildManifest(directory):
    """Build a manifest from the contents of the given directory, into the
    given directory."""

    manifestPath = os.path.join(directory, manifestName)
    try:
        os.remove(manifestPath)
    except:
        pass
    
    manifest = Manifest()
    manifest.addFiles(directory, [])
    with open(manifestPath, "wt") as f:
        manifest.writeInto(f)

#------------------------------------------------------------------------------

# if __name__ == "__main__":
#     manifest1 = Manifest()
#     manifest1.addFile("file1.exe", 3242, "40398754589435345934")
#     manifest1.addFile("dir/file2.zip", 45645, "347893245873456987")
#     manifest1.addFile("dir/file3.txt", 123, "3432434534534534")

#     with open("manifest1", "wt") as f:
#         manifest1.writeInto(f)

#     manifest2 = Manifest()
#     manifest2.addFile("file1.exe", 4353, "390734659834756349876")
#     manifest2.addFile("dir/file2.zip", 45645, "347893245873456987")
#     manifest2.addFile("dir/file4.log", 2390, "56546546546546")

#     with open("manifest2", "wt") as f:
#         manifest2.writeInto(f)

#     manifest1 = Manifest()
#     with open("manifest1", "rt") as f:
#         manifest1.readFrom(f)

#     manifest2 = Manifest()
#     with open("manifest2", "rt") as f:
#         manifest2.readFrom(f)

#     (modifiedAndNew, removed) = manifest1.compare(manifest2)

#     for (path, size, sum) in modifiedAndNew:
#         print "modified or new:", path, size, sum

#     for path in removed:
#         print "removed:", path

#------------------------------------------------------------------------------
