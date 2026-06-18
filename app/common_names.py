# ════════════════════════════════════════════════════════
# Common Names Dictionary — Sikar/Rajasthan Region
# ════════════════════════════════════════════════════════
# Used as a SECONDARY reference for name auto-correct when a
# customer's name doesn't exist in the live database yet
# (i.e. their very first order). This catches common spelling
# variations for names that are very frequent in this region,
# even before the customer has ever ordered before.
#
# Format: canonical (correct) spelling. The matching logic in
# employee.py normalizes case/spacing/honorifics before
# comparing, so "ramesh", "RAMESH", "ramesh ji" etc. all match.
# ════════════════════════════════════════════════════════

COMMON_NAMES = [
    # ── Common male first names (Rajasthan/Hindi belt) ──
    "Ramesh", "Suresh", "Mahesh", "Naresh", "Rajesh", "Mukesh", "Dinesh",
    "Lokesh", "Hitesh", "Jitesh", "Nilesh", "Yogesh", "Paresh", "Umesh",
    "Ganesh", "Kamlesh", "Mahendra", "Surendra", "Narendra", "Devendra",
    "Jitendra", "Rajendra", "Birendra", "Yogendra", "Mukundra", "Bhupendra",
    "Virendra", "Dharmendra", "Sanjay", "Vijay", "Ajay", "Akshay",
    "Sandeep", "Pradeep", "Sudeep", "Mandeep", "Gurdeep", "Amit", "Sumit",
    "Rohit", "Mohit", "Lalit", "Ankit", "Rahul", "Rakesh", "Subhash",
    "Prakash", "Ashok", "Pawan", "Gagan", "Naveen", "Praveen", "Sandhya",
    "Sachin", "Nitin", "Manish", "Anish", "Harish", "Girish", "Satish",
    "Yatish", "Manoj", "Sanjeev", "Rajeev", "Sanjiv", "Vinod", "Pramod",
    "Vishal", "Deepak", "Gopal", "Madan", "Mohan", "Sohan", "Rohan",
    "Kishan", "Roshan", "Darshan", "Karan", "Arjun", "Tarun", "Varun",
    "Kiran", "Sajjan", "Hawa Singh", "Bhanwar", "Bhanwarlal", "Chunnilal",
    "Sispal", "Shishpal", "Inder", "Indraj", "Surajmal", "Suraj",
    "Banwarilal", "Banshilal", "Gangaram", "Gangasahay", "Sitaram", "Ramprasad",
    "Shivprasad", "Jagdish", "Mahadev", "Sukhdev", "Brijesh", "Brijmohan",
    "Mohanlal", "Shyamlal", "Ramlal", "Hanslal", "Nathulal", "Bhagwan",
    "Bhagwandas", "Bhagwati", "Bhanwarsingh", "Kalyan", "Kalyanmal", "Onkar",
    "Omprakash", "Hariprasad", "Sitaprasad", "Sohanlal", "Surajbhan",
    "Hemraj", "Hiraj", "Mangilal", "Mangal", "Mangalsingh", "Bhairu",
    "Bhairulal", "Manaklal", "Manakchand", "Sukhram", "Sukhlal", "Chhotulal",
    "Chhotu", "Kamlesh", "Kanhaiyalal", "Kishanlal", "Govind", "Govindram",
    "Narayan", "Narayanlal", "Vishnu", "Shankar", "Shankarlal", "Bholaram",
    "Bholanath", "Pannalal", "Heeralal", "Heera", "Moolchand", "Moti",
    "Motilal", "Babulal", "Babu", "Phoolchand", "Phool", "Ratan",
    "Ratanlal", "Lalchand", "Lal", "Devisingh", "Devkaran", "Devaram",
    "Premsukh", "Prem", "Premchand", "Vijaysingh", "Vikram", "Vikramsingh",
    "Mahaveer", "Mahaveersingh", "Govindsingh", "Jaisingh", "Jairam",
    "Ramswaroop", "Swaroop", "Nathu", "Madho", "Madhosingh", "Bhopalsingh",
    "Hukamchand", "Hukam", "Khushal", "Khushalchand", "Chainram", "Chain",
    "Khemraj", "Khema", "Pukhraj", "Sohanram", "Mishrilal", "Mishri",
    "Daulatram", "Daulat", "Onkarmal", "Hardayal", "Hardev", "Harnarayan",
    "Tejaram", "Teja", "Tejpal", "Tejsingh", "Madanlal", "Madansingh",
    "Bansilal", "Bansi", "Nandlal", "Nandkishore", "Kishorilal", "Kishore",
    "Bhanwarlal", "Indarmal", "Indarchand", "Chhaganlal", "Chhagan",
    "Hardevsingh", "Ramavtar", "Avtar", "Mahipal", "Mahipalsingh",

    # ── Common with "ji" honorific (will normalize automatically) ──
    "Sispal Ji", "Chunnilal Ji", "Bhanwarlal Ji", "Nathulal Ji",
    "Mohanlal Ji", "Shyamlal Ji", "Ramlal Ji", "Pannalal Ji",
    "Heeralal Ji", "Motilal Ji", "Babulal Ji", "Phoolchand Ji",
    "Ratanlal Ji", "Lalchand Ji", "Bansilal Ji", "Nandlal Ji",
    "Chhaganlal Ji", "Mishrilal Ji", "Daulatram Ji", "Hukamchand Ji",
    "Khushalchand Ji", "Tejaram Ji", "Madanlal Ji", "Kishanlal Ji",
    "Govindram Ji", "Narayanlal Ji", "Shankarlal Ji", "Bholaram Ji",
    "Moolchand Ji", "Premchand Ji", "Indarmal Ji", "Onkarmal Ji",
    "Surajmal Ji", "Banwarilal Ji", "Banshilal Ji", "Gangaram Ji",
    "Sitaram Ji", "Ramprasad Ji", "Shivprasad Ji", "Jagdish Ji",
    "Mahadev Ji", "Sukhdev Ji", "Brijmohan Ji", "Hanslal Ji",
    "Bhagwandas Ji", "Mangilal Ji", "Bhairulal Ji", "Manakchand Ji",
    "Sukhram Ji", "Chhotulal Ji", "Kanhaiyalal Ji", "Kishorilal Ji",

    # ── Common female first names ──
    "Sunita", "Anita", "Geeta", "Sita", "Rita", "Kavita", "Savita",
    "Babita", "Lalita", "Mamta", "Vimla", "Kamla", "Shanti", "Santosh",
    "Sushila", "Pushpa", "Sarla", "Nirmala", "Shobha", "Asha", "Usha",
    "Meena", "Rekha", "Seema", "Neelam", "Kiran", "Sangeeta", "Sunaina",
    "Madhuri", "Manju", "Manjula", "Saroj", "Sarita", "Pinky", "Reena",
    "Renu", "Ritu", "Poonam", "Pooja", "Priya", "Priyanka", "Komal",
    "Kanchan", "Suman", "Sumitra", "Indira", "Indra", "Vidya", "Radha",
    "Krishna", "Durga", "Lakshmi", "Saraswati", "Parvati", "Gayatri",
    "Premlata", "Premsheela", "Hemlata", "Sheela", "Kamla Devi", "Kalavati",

    # ── Common surnames/titles (Rajasthan region) ──
    "Sharma", "Verma", "Gupta", "Agarwal", "Jain", "Kumawat", "Saini",
    "Yadav", "Meena", "Gurjar", "Rajput", "Choudhary", "Chaudhary",
    "Bishnoi", "Jat", "Mali", "Brahmin", "Khatri", "Soni", "Suthar",
    "Kumhar", "Nai", "Dhobi", "Bairwa", "Regar", "Mehta", "Joshi",
    "Pareek", "Vyas", "Trivedi", "Pandit", "Dave", "Acharya",
]

# Pre-normalized lookup set (lowercase, ji-stripped) built at import time
def _normalize(s):
    s = s.lower().strip()
    for suffix in [" jee", " jii", " ji", "jee", "jii"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    return " ".join(s.split())

COMMON_NAMES_LOOKUP = {_normalize(n): n for n in COMMON_NAMES}
