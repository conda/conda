from __future__ import print_function
import re

def win_path_list_to_unix(path):
    path_re = re.compile('[a-zA-Z]:\\\\(?:[^:*?"<>|]+\\\\)*[^:*?"<>|;]+')
    converted_paths = ["/" + _path.replace("\\", "/").replace(":", "")
                       for _path in path_re.findall(path)]
    return ":".join(converted_paths)

def unix_path_to_win(path):
    path_re = re.compile('\/[a-zA-Z]\/(?:[^:*?"<>|]+\\\\)*[^:*?"<>|;]+')
    converted_paths = [_path[1] + ":" + _path[2:].replace("/", "\\")
                       for _path in path_re.findall(path)]
    return ";".join(converted_paths)

if __name__ == "__main__":
    test_unix_path = \z\Documents\code\conda\tests\envsmrsxz9\test1:\z\Documents\code\conda\tests\envsmrsxz9\test1\cmd:\z\Documents\code\conda\tests\envsmrsxz9\test1\Scripts:\z\Documents\code\conda\tests\envsmrsxz9\test1\Library\bin:\usr\local\bin:\usr\bin:\usr\bin:\c\Miniconda2\Library\bin:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\intel64_win\mpirt:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\ia32_win\mpirt:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\intel64_win\compiler:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\ia32_win\compiler:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\intel64_win\mpirt:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\ia32_win\mpirt:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\intel64_win\compiler:\c\Program Files (x86)\Common Files\Intel\Shared Libraries\redist\ia32_win\compiler:\c\Perl\site\bin:\c\Perl\bin:\c\WINDOWS\system32:\c\WINDOWS:\c\WINDOWS\System32\Wbem:\c\WINDOWS\System32\WindowsPowerShell\v1.0:\c\Program Files (x86)\Windows Kits\8.1\Windows Performance Toolkit:\c\ProgramData\chocolatey\bin:\c\Program Files (x86)\Windows Kits\10\Windows Performance Toolkit:\c\Program Files\gs\gs9.18\bin:\c\Program Files (x86)\MiKTeX 2.9\miktex\bin:\c\WINDOWS\system32:\c\WINDOWS:\c\WINDOWS\System32\Wbem:\c\WINDOWS\System32\WindowsPowerShell\v1.0:\c\Users\builder\AppData\Local\Programs\Python\Launcher:\c\Users\builder\Miniconda2:\c\Users\builder\Miniconda2\Scripts:\c\Users\builder\Miniconda2\Library\bin
    test_win_path = "z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd"
    assert test_win_path == unix_path_to_win(test_unix_path)
    assert test_unix_path.replace("/usr/bin:", "") == win_path_list_to_unix(test_win_path)
