# MetadataRemoval
Removes Metadata from files.  AKA metadata scrubbing.


### Why?  

The problem:  

A crucial step in the cyber kill chain is reconnaissance, where an attacker scopes at the target using open source intelligence tools and skills to find "vulnerable" spots to enter from.  

Attackers and anyone in general can easily access public files from a website using a google search like `site:website-name filetype:filetype` (ie. `site:aws.amazon.com filetype:pdf` to look for pdf's on amazon).  

These files can contain metadata that shows the kind of software and software versions a company might use.  

Hackers will then try to exploit these software versions but looking for any unpatched vulnerabilities.  

---

### One solution that I am covering here is to remove file metadata from any files published online in an attempt to reduce a company's attack surface area.


---

## Instructions:  

1. Install exiftool `sudo apt install libimage-exiftool-perl`
2. Run `exiftool "file-to-be-scrubbed.pdf"`


<br />
<br />
<br />
<br />

Further OSINT reconnaissance mitigation topics I'd like to cover later on:
- Webscraping
- Email address obfuscation
- Social media privacy
- Network exposure (ports)
- Job posting sanitization
