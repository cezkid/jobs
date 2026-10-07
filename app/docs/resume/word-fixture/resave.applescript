-- Word for Mac re-saves the source as its own .docx and exports a PDF (Quartz print path, not
-- Windows Word's exporter). Paths inside Word's sandbox avoid a file-access prompt:
-- ~/Library/Containers/com.microsoft.Word/Data/Documents/jf-fixture/
-- osascript resave.applescript <folder>
on run argv
	set dir to item 1 of argv
	tell application "Microsoft Word"
		open file name (POSIX file (dir & "/source.docx") as text)
		delay 2
		set d to active document
		save as d file name (POSIX file (dir & "/word-resume.docx") as text) file format format document
		delay 1
		save as d file name (POSIX file (dir & "/word-resume.pdf") as text) file format format PDF
		delay 2
		close d saving no
	end tell
end run
