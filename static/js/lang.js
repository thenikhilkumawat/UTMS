// ═══════════════════════════════════════════════════
//  UTTAM TAILORS — Complete Translation Dictionary
//  EN = English | HI = Hindi | HL = Hinglish
// ═══════════════════════════════════════════════════

const T = {
  // ── Navigation
  dashboard:         {en:"Dashboard",               hi:"मुख्य पेज",              hl:"Dashboard"},
  new_order:         {en:"New Order",                hi:"नया ऑर्डर",               hl:"New Order"},
  order_status:      {en:"Order Status",             hi:"ऑर्डर स्थिति",            hl:"Order Status"},
  delivery_schedule: {en:"Delivery Schedule",        hi:"डिलीवरी शेड्यूल",         hl:"Delivery Schedule"},
  work_log:          {en:"Work Log",                 hi:"काम की जानकारी",          hl:"Work Log"},
  pickup_delivery:   {en:"Pickup & Delivery",        hi:"पिकअप व डिलीवरी",         hl:"Pickup & Delivery"},
  finance:           {en:"Finance",                  hi:"हिसाब-किताब",              hl:"Finance"},
  inventory:         {en:"Inventory",                hi:"सामान का स्टॉक",           hl:"Inventory"},
  customers:         {en:"Customers",                hi:"ग्राहक",                  hl:"Customers"},
  settings:          {en:"Settings",                 hi:"सेटिंग्स",                hl:"Settings"},
  owner_login:       {en:"Admin",                    hi:"एडमिन",              hl:"Owner Login"},
  owner_area:        {en:"Owner Area",               hi:"मालिक क्षेत्र",             hl:"Owner Area"},
  logout:            {en:"Logout",                   hi:"लॉग आउट",                 hl:"Logout"},
  send_whatsapp:     {en:"WhatsApp",                 hi:"व्हाट्सऐप",               hl:"WhatsApp"},
  owner_dashboard:   {en:"Owner Dashboard",          hi:"मालिक डैशबोर्ड",          hl:"Owner Dashboard"},

  // ── Common actions
  save:              {en:"Save",                     hi:"सेव करें",                hl:"Save karein"},
  cancel:            {en:"Cancel",                   hi:"रद्द करें",               hl:"Cancel karein"},
  search:            {en:"Search",                   hi:"खोजें",                   hl:"Search karein"},
  back:              {en:"Back",                     hi:"वापस",                    hl:"Back"},
  view:              {en:"View",                     hi:"देखें",                   hl:"View"},
  edit:              {en:"Edit",                     hi:"बदलें",                   hl:"Edit"},
  delete:            {en:"Delete",                   hi:"हटाएं",                   hl:"Delete"},
  add:               {en:"Add",                      hi:"जोड़ें",                   hl:"Add"},
  remove:            {en:"Remove",                   hi:"हटाएं",                   hl:"Remove"},
  close:             {en:"Close",                    hi:"बंद करें",                hl:"Close"},
  confirm:           {en:"Confirm",                  hi:"पक्का करें",              hl:"Confirm"},
  submit:            {en:"Submit",                   hi:"जमा करें",                hl:"Submit"},
  loading:           {en:"Loading...",               hi:"लोड हो रहा है...",        hl:"Loading..."},
  print_slip:        {en:"Print Slip",               hi:"पर्ची प्रिंट करें",        hl:"Print Slip"},

  // ── Dashboard
  quick_actions:     {en:"Quick Actions",            hi:"जल्दी काम",               hl:"Quick Actions"},
  todays_orders:     {en:"Today's Orders",           hi:"आज के ऑर्डर",             hl:"Aaj ke Orders"},
  urgent_orders:     {en:"Urgent Orders",            hi:"जरूरी ऑर्डर",             hl:"Urgent Orders"},
  pending_delivery:  {en:"Pending Delivery",         hi:"डिलीवरी बाकी",            hl:"Pending Delivery"},
  urgent_today:      {en:"Urgent",                   hi:"जरूरी",                   hl:"Urgent"},
  rate_list:         {en:"Rate List",                hi:"रेट लिस्ट",               hl:"Rate List"},
  customer_rate_list:{en:"Customer Rate List",       hi:"ग्राहक दर सूची",          hl:"Customer Rate List"},
  no_urgent_orders:  {en:"No urgent orders",         hi:"कोई जरूरी ऑर्डर नहीं",    hl:"Koi urgent order nahi"},
  all_good:          {en:"All good!",                hi:"सब ठीक है!",              hl:"Sab theek hai!"},
  view_schedule:     {en:"View delivery schedule →", hi:"डिलीवरी शेड्यूल देखें →", hl:"Schedule dekhein →"},
  handle_first:      {en:"Handle these first →",     hi:"पहले इन्हें देखें →",      hl:"Pehle ye dekho →"},
  collect_deliver:   {en:"Collect & deliver →",      hi:"लें और दें →",             hl:"Lo aur do →"},
  create_order:      {en:"Create order for customer",hi:"ग्राहक का ऑर्डर बनाएं",   hl:"Customer ka order banao"},
  view_schedule2:    {en:"View delivery schedule",   hi:"डिलीवरी शेड्यूल देखें",    hl:"Schedule dekho"},
  log_stitching:     {en:"Log stitching progress",   hi:"सिलाई की जानकारी दर्ज करें",hl:"Stitching log karo"},
  collect_pay:       {en:"Collect payment & deliver",hi:"पैसे लो और डिलीवर करो",   hl:"Payment lo aur deliver karo"},
  todays_expenses:   {en:"Today's income & expenses",hi:"आज की आमदनी और खर्च",     hl:"Aaj ki income & expense"},
  access_owner:      {en:"Access owner dashboard",   hi:"मालिक डैशबोर्ड खोलें",    hl:"Owner dashboard kholo"},

  // ── Order Status
  all_orders:        {en:"All Orders",               hi:"सभी ऑर्डर",               hl:"All Orders"},
  late:              {en:"Late",                     hi:"देरी",                    hl:"Late"},
  upcoming:          {en:"Upcoming",                 hi:"आने वाला",                hl:"Upcoming"},
  ready:             {en:"Ready",                    hi:"तैयार",                   hl:"Ready"},
  delivered:         {en:"Delivered",                hi:"डिलीवर हो गया",           hl:"Delivered"},
  pending:           {en:"Pending",                  hi:"बाकी है",                 hl:"Pending"},
  in_progress:       {en:"In Progress",              hi:"काम चल रहा है",           hl:"In Progress"},
  delivery_date:     {en:"Delivery Date",            hi:"डिलीवरी तारीख",           hl:"Delivery Date"},
  order_info:        {en:"Order Info",               hi:"ऑर्डर जानकारी",           hl:"Order Info"},
  payment_status:    {en:"Payment",                  hi:"भुगतान",                  hl:"Payment"},
  work_progress:     {en:"Progress",                 hi:"प्रगति",                  hl:"Progress"},
  status:            {en:"Status",                   hi:"स्थिति",                  hl:"Status"},
  actions:           {en:"Actions",                  hi:"काम",                     hl:"Actions"},
  fully_paid:        {en:"Fully Paid",               hi:"पूरा भुगतान",             hl:"Fully Paid"},
  due:               {en:"Due",                      hi:"बकाया",                   hl:"Due"},
  advance_paid:      {en:"Advance Paid",             hi:"अग्रिम राशि",             hl:"Advance Paid"},
  notify_customer:   {en:"Notify Customer",          hi:"ग्राहक को बताएं",         hl:"Notify karo"},
  notify:            {en:"📲 Notify",                hi:"📲 सूचित करें",           hl:"📲 Notify"},
  working:           {en:"Working",                  hi:"काम हो रहा है",           hl:"Working"},
  go_pickup:         {en:"Go to Pickup & Delivery",  hi:"पिकअप पेज जाएं",          hl:"Pickup page jao"},
  garments_meas:     {en:"Garments & Measurements",  hi:"कपड़े और नाप",            hl:"Kapde & Measurements"},
  order_details:     {en:"Order Details",            hi:"ऑर्डर विवरण",             hl:"Order Details"},
  total_bill:        {en:"Total Bill",               hi:"कुल बिल",                 hl:"Total Bill"},
  remaining:         {en:"Remaining",                hi:"बकाया",                   hl:"Remaining"},
  order_date:        {en:"Order Date",               hi:"ऑर्डर तारीख",             hl:"Order Date"},
  payment_mode:      {en:"Payment Mode",             hi:"भुगतान का तरीका",          hl:"Payment Mode"},

  // ── Work Log
  select_employee:   {en:"Select Employee",          hi:"कर्मचारी चुनें",           hl:"Employee chuno"},
  log_work:          {en:"Log Work",                 hi:"काम दर्ज करें",           hl:"Kaam log karo"},
  for_label:         {en:"For",                      hi:"के लिए",                  hl:"Ke liye"},
  order_code:        {en:"Order Code",               hi:"ऑर्डर नंबर",              hl:"Order Code"},
  qty_done:          {en:"Quantity Done",            hi:"किए हुए कपड़े",            hl:"Qty Done"},
  notes_optional:    {en:"Notes (Optional)",         hi:"टिप्पणी (वैकल्पिक)",      hl:"Notes (Optional)"},
  pieces_done:       {en:"Pieces Done",              hi:"बने कपड़े",               hl:"Pieces Done"},
  orders_worked:     {en:"Orders Worked",            hi:"ऑर्डर पर काम",            hl:"Orders Worked"},
  earnings_est:      {en:"Earnings Est.",            hi:"अनुमानित कमाई",           hl:"Earnings Est."},
  this_week:         {en:"This Week",                hi:"इस हफ्ते",                hl:"Is Hafte"},
  this_month:        {en:"This Month",               hi:"इस महीने",                hl:"Is Mahine"},
  work_summary:      {en:"Work Summary",             hi:"काम का सारांश",           hl:"Kaam Summary"},
  no_work_logged:    {en:"No work logged",           hi:"कोई काम दर्ज नहीं",        hl:"Koi kaam log nahi"},

  // ── Pickup & Delivery
  find_order:        {en:"Find Order",               hi:"ऑर्डर ढूंढें",            hl:"Order dhundho"},
  search_order:      {en:"Search by code, name or mobile", hi:"ऑर्डर कोड, नाम या मोबाइल से खोजें", hl:"Code, naam ya mobile se search karo"},
  collect_payment:   {en:"Collect Payment",          hi:"पैसे लें",                hl:"Payment lo"},
  mark_delivered:    {en:"Mark as Delivered",        hi:"डिलीवर करें",             hl:"Deliver karo"},
  collect_deliver2:  {en:"Collect & Mark Delivered", hi:"पैसे लो और डिलीवर करो",  hl:"Collect & Deliver"},
  amount_label:      {en:"Amount (₹)",               hi:"रकम (₹)",                hl:"Amount (₹)"},
  mode:              {en:"Mode",                     hi:"तरीका",                   hl:"Mode"},
  cash:              {en:"Cash",                     hi:"नकद",                     hl:"Cash"},
  upi:               {en:"UPI",                      hi:"यूपीआई",                  hl:"UPI"},
  garments:          {en:"Garments",                 hi:"कपड़े",                   hl:"Kapde"},
  cloth_images:      {en:"Cloth Images",             hi:"कपड़े की फोटो",            hl:"Cloth Images"},
  already_delivered: {en:"Already Delivered",        hi:"पहले डिलीवर हो चुका",    hl:"Already Delivered"},
  cannot_deliver:    {en:"Cannot Deliver — Still Pending", hi:"डिलीवर नहीं — अभी बाकी है", hl:"Cannot Deliver — Pending hai"},
  search_another:    {en:"← Search Another Order",  hi:"← दूसरा ऑर्डर खोजें",    hl:"← Doosra Order search karo"},

  // ── Finance
  add_entry:         {en:"Add Entry",                hi:"एंट्री जोड़ें",            hl:"Entry add karo"},
  income:            {en:"Income",                   hi:"आमदनी",                   hl:"Income"},
  expense:           {en:"Expense",                  hi:"खर्च",                    hl:"Kharcha"},
  net_profit:        {en:"Net Profit",               hi:"शुद्ध मुनाफा",             hl:"Net Profit"},
  todays_income:     {en:"Today's Income",           hi:"आज की कमाई",              hl:"Aaj ki Income"},
  todays_expense:    {en:"Today's Expense",          hi:"आज का खर्च",              hl:"Aaj ka Kharcha"},
  yesterdays_income: {en:"Yesterday's Income",       hi:"कल की कमाई",              hl:"Kal ki Income"},
  yesterdays_expense:{en:"Yesterday's Expense",      hi:"कल का खर्च",              hl:"Kal ka Kharcha"},
  category:          {en:"Category",                 hi:"वर्ग",                    hl:"Category"},
  amount:            {en:"Amount",                   hi:"रकम",                     hl:"Amount"},
  note_field:        {en:"Note",                     hi:"टिप्पणी",                 hl:"Note"},
  transactions:      {en:"Transactions",             hi:"लेनदेन",                  hl:"Transactions"},
  today_filter:      {en:"Today",                    hi:"आज",                      hl:"Aaj"},
  yesterday_filter:  {en:"Yesterday",                hi:"कल",                      hl:"Kal"},
  no_transactions:   {en:"No transactions yet",      hi:"कोई लेनदेन नहीं",         hl:"Koi transaction nahi"},

  // ── Garment types
  "Shirt":           {en:"Shirt",         hi:"शर्ट",          hl:"Shirt"},
  "Shirt Linen":     {en:"Shirt Linen",   hi:"लिनन शर्ट",     hl:"Linen Shirt"},
  "Pant":            {en:"Pant",          hi:"पैंट",           hl:"Pant"},
  "Pant Double":     {en:"Pant Double",   hi:"डबल पैंट",       hl:"Double Pant"},
  "Jeans":           {en:"Jeans",         hi:"जींस",           hl:"Jeans"},
  "Suit 2pc":        {en:"Suit 2pc",      hi:"सूट 2 पीस",     hl:"Suit 2pc"},
  "Suit 3pc":        {en:"Suit 3pc",      hi:"सूट 3 पीस",     hl:"Suit 3pc"},
  "Blazer":          {en:"Blazer",        hi:"ब्लेजर",         hl:"Blazer"},
  "Kurta":           {en:"Kurta",         hi:"कुर्ता",          hl:"Kurta"},
  "Kurta Pajama":    {en:"Kurta Pajama",  hi:"कुर्ता पाजामा",   hl:"Kurta Pajama"},
  "Pajama":          {en:"Pajama",        hi:"पाजामा",         hl:"Pajama"},
  "Pathani":         {en:"Pathani",       hi:"पठानी",          hl:"Pathani"},
  "Sherwani":        {en:"Sherwani",      hi:"शेरवानी",        hl:"Sherwani"},
  "Safari":          {en:"Safari",        hi:"सफारी",          hl:"Safari"},
  "Waistcoat":       {en:"Waistcoat",     hi:"वेस्टकोट",       hl:"Waistcoat"},
  "Alteration":      {en:"Alteration",    hi:"बदलाव",          hl:"Alteration"},
  "Cutting Only":    {en:"Cutting Only",  hi:"सिर्फ कटिंग",    hl:"Sirf Cutting"},

  // ── Measurements
  // Measurement fields - Hindi names
  lambai:     {en:"Lambai",    hi:"लंबाई"},
  seeno:      {en:"Seeno",     hi:"सीना"},
  kamar:      {en:"Kamar",     hi:"कमर"},
  seat:       {en:"Seat",      hi:"सीट"},
  mori:       {en:"Mori",      hi:"मोरी"},
  jangh:      {en:"Jangh",     hi:"जांघ"},
  goda:       {en:"Goda",      hi:"घुटना"},
  langot:     {en:"Langot",    hi:"लंगोट"},
  shoulder:   {en:"Shoulder",  hi:"कंधा"},
  collar:     {en:"Collar",    hi:"कॉलर"},
  aastin:     {en:"Aastin",    hi:"आस्तीन"},
  cough:      {en:"Cough",     hi:"कफ"},
  back_paat:  {en:"Back Paat", hi:"बैक पाट"},
  part1:      {en:"Part 1",    hi:"पाट 1"},
  part2:      {en:"Part 2",    hi:"पाट 2"},
  part3:      {en:"Part 3",    hi:"पाट 3"},
  p_lambai:   {en:"P-Lambai",  hi:"पाय. लंबाई"},
  p_kamar:    {en:"P-Kamar",   hi:"पाय. कमर"},
  p_seat:     {en:"P-Seat",    hi:"पाय. सीट"},
  p_mori:     {en:"P-Mori",    hi:"पाय. मोरी"},
  p_jangh:    {en:"P-Jangh",   hi:"पाय. जांघ"},
  hip:        {en:"Hip",       hi:"हिप"},
  details:    {en:"Details",   hi:"विवरण"},
  length:     {en:"Lambai",    hi:"लंबाई"},
  chest:      {en:"Seeno",     hi:"सीना"},
  waist:      {en:"Kamar",     hi:"कमर"},
  thigh:      {en:"Jangh",     hi:"जांघ"},
  bottom:     {en:"Mori",      hi:"मोरी"},

  // ── New Order
  new_customer:      {en:"New Customer",        hi:"नया ग्राहक",         hl:"New Customer"},
  existing_customer: {en:"Existing Customer",   hi:"पुराना ग्राहक",      hl:"Existing Customer"},
  first_time:        {en:"First time visit",    hi:"पहली बार आए",        hl:"Pehli baar aaye"},
  returning:         {en:"Returning customer",  hi:"पुराना ग्राहक है",    hl:"Purana customer hai"},
  step_garments:     {en:"Garments",            hi:"कपड़े",               hl:"Kapde"},
  step_images:       {en:"Images",              hi:"फोटो",                hl:"Photos"},
  step_customer:     {en:"Customer",            hi:"ग्राहक",              hl:"Customer"},
  step_payment:      {en:"Payment",             hi:"भुगतान",              hl:"Payment"},
  add_garment:       {en:"Add Garments",        hi:"कपड़े जोड़ें",         hl:"Kapde add karo"},
  garment_type:      {en:"Garment Type",        hi:"कपड़े का प्रकार",      hl:"Garment Type"},
  quantity:          {en:"Qty",                 hi:"संख्या",              hl:"Qty"},
  rate:              {en:"Rate ₹",              hi:"दर ₹",                hl:"Rate ₹"},
  total:             {en:"Total",               hi:"कुल",                 hl:"Total"},
  extra_charges:     {en:"Extra Charges",       hi:"अतिरिक्त चार्ज",      hl:"Extra Charges"},
  payable:           {en:"Net Payable",         hi:"कुल देय राशि",         hl:"Net Payable"},
  advance:           {en:"Advance Paid",        hi:"अग्रिम राशि",          hl:"Advance Paid"},
  customer_name:     {en:"Customer Name",       hi:"ग्राहक का नाम",        hl:"Customer Name"},
  mobile:            {en:"Mobile Number",       hi:"मोबाइल नंबर",          hl:"Mobile Number"},
  address:           {en:"Address",             hi:"पता",                  hl:"Address"},
  delivery_date2:    {en:"Delivery Date",       hi:"डिलीवरी की तारीख",    hl:"Delivery Date"},
  special_note:      {en:"Special Note",        hi:"खास टिप्पणी",         hl:"Special Note"},
  measurements:      {en:"Measurements",        hi:"नाप",                  hl:"Measurements"},
  urgent_order:      {en:"Mark as Urgent",      hi:"जरूरी ऑर्डर करें",    hl:"Urgent mark karo"},
  confirm_order:     {en:"Confirm Order",       hi:"ऑर्डर पक्का करें",    hl:"Order confirm karo"},
};

// Measurement field key mapping
const FIELD_KEY = {
  // Old English names
  "Length":"lambai","Chest":"seeno","Waist":"kamar","Hip":"hip",
  "Shoulder":"shoulder","Sleeve":"aastin","Collar":"collar",
  "Thigh":"jangh","Bottom":"mori","Details":"details","Sleeve":"aastin",
  // New Hindi names map directly to their Hindi translations
  "Lambai":"lambai","Seeno":"seeno","Kamar":"kamar","Mori":"mori",
  "Jangh":"jangh","Goda":"goda","Langot":"langot","Seat":"seat",
  "Aastin":"aastin","Cough":"cough","Back Paat":"back_paat",
  "Part 1":"part1","Part 2":"part2","Part 3":"part3",
  "P-Lambai":"p_lambai","P-Kamar":"p_kamar","P-Seat":"p_seat",
  "P-Mori":"p_mori","P-Jangh":"p_jangh"
};

let currentLang = localStorage.getItem("utms_lang") || "en";
// Only EN and HI supported
if (currentLang === "hl") { currentLang = "en"; localStorage.setItem("utms_lang","en"); }

function t(key) {
  var entry = T[key];
  if (!entry) return key;
  return entry[currentLang] || entry["en"] || key;
}

function tField(f) {
  var k = FIELD_KEY[f];
  if (!k) return f;
  var entry = T[k];
  if (!entry) return f;
  return entry[currentLang] || entry["en"] || f;
}

function tGarment(g) {
  var e = T[g];
  return (e && e[currentLang]) ? e[currentLang] : g;
}

function setLang(lang) {
  currentLang = lang;
  localStorage.setItem("utms_lang", lang);
  applyLang();
  if (typeof renderGarments === "function") renderGarments();
  if (typeof renderExistingGarments === "function") renderExistingGarments();
  if (typeof updateSelectOptions === "function") updateSelectOptions();
}

function applyLang() {
  // Pure language switching - no mixing
  document.querySelectorAll("[data-t]").forEach(function(el) {
    var key = el.getAttribute("data-t");
    var val = t(key);
    if (val !== key) el.textContent = val;
  });
  // Translate [data-tp] placeholders
  document.querySelectorAll("[data-tp]").forEach(function(el) {
    var key = el.getAttribute("data-tp");
    var val = t(key);
    if (val !== key) el.placeholder = val;
  });
  // Active lang button styling
  document.querySelectorAll(".lang-btn").forEach(function(btn) {
    var active = btn.dataset.lang === currentLang;
    btn.classList.toggle("active", active);
  });
  // Garment select options
  document.querySelectorAll("option[data-garment]").forEach(function(opt) {
    var tr = tGarment(opt.dataset.garment);
    opt.textContent = tr;
  });
  // Garment display elements (non-option)
  document.querySelectorAll("[data-garment]:not(option)").forEach(function(el) {
    el.textContent = tGarment(el.dataset.garment);
  });
  // Measurement labels
  document.querySelectorAll("[data-field]").forEach(function(el) {
    el.textContent = tField(el.dataset.field);
  });
  // Pure language class toggling
  var isHi = (currentLang === "hi");
  document.querySelectorAll(".lang-en").forEach(function(el) {
    el.style.display = isHi ? "none" : "";
  });
  document.querySelectorAll(".lang-hi").forEach(function(el) {
    el.style.display = isHi ? "" : "none";
  });
  document.documentElement.lang = isHi ? "hi" : "en";
}

document.addEventListener("DOMContentLoaded", applyLang);
