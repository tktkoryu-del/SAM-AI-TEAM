# SAM Recovery — Native MVP

واجهة عربية أولية للعثور على الصور والفيديوهات المتاحة محلياً، مع احترام صلاحيات النظام.

## ما يعمل في هذا الأساس البرمجي
- Android: طلب صلاحيات الوسائط الحديثة، قراءة عناصر MediaStore المتاحة، عرض الاسم والتاريخ، فتح العنصر عبر تطبيق مناسب، ونسخ الملف إلى وجهة يختارها المستخدم عبر SAF.
- iOS: طلب إذن PhotoKit بمستوى read/write، دعم حالة limited، وعرض عناصر الصور والفيديوهات التي يسمح النظام للتطبيق برؤيتها.
- لا توجد خدمة خلفية أو رفع ملفات أو تحليلات في هذا الإصدار.

## ما لا يدّعيه التطبيق
- لا يستعيد كتل التخزين التي حُذفت نهائياً.
- لا يتجاوز تشفير النظام أو sandbox أو صلاحيات المستخدم.
- لا يقرأ ألبوم Recently Deleted في iOS من خارج تطبيق Photos.
- لا يضمن العثور على عناصر غير متاحة من خلال واجهات النظام.

## بناء Android محلياً
المتطلبات: JDK 17، Android SDK Platform 36، Gradle 8.13.
```bash
cd projects/sam-recovery/android
gradle assembleDebug
```
الناتج المتوقع عند نجاح البناء:
`app/build/outputs/apk/debug/app-debug.apk`

## بناء iOS
المتطلبات: macOS، Xcode، XcodeGen.
```bash
cd projects/sam-recovery/ios
xcodegen generate
xcodebuild -scheme SAMRecovery -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
```

## الخصوصية
الفحص محلي. لا تطلب صلاحيات شاملة للتخزين، ولا ترسل أسماء الملفات أو محتواها إلى خادم.

## الحالة
هذا MVP أولي وليس إصدار متجر. لم يُثبت بعد نجاح build على runner أو جهاز فعلي. لا يُنشر قبل نجاح CI، واختبار مصفوفة الصلاحيات، ومراجعة الخصوصية وإمكانية الوصول.