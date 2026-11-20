# SAM Recovery — القرار المعماري الأولي

## القرار
اعتماد تطبيقين أصليين منفصلين للمرحلة الأولى:
- Android: Kotlin + Jetpack Compose + Coroutines/Flow.
- iOS: Swift + SwiftUI + PhotoKit.

السبب: الوصول إلى مكتبات الوسائط والصلاحيات وسلوك سلال المحذوفات مرتبط بواجهات النظام، والتنفيذ الأصلي يقلل طبقات الوساطة ويتيح اختباراً أوضح. لا يُعتمد إطار متعدد المنصات قبل إثبات أن واجهات النظام المطلوبة مدعومة دون تنازلات.

## طبقات التطبيق
1. Presentation: الشاشات، RTL، حالات التحميل والخطأ والفراغ.
2. Domain: حالات الاستخدام، نماذج النتائج، سياسات إظهار قابلية الاستعادة.
3. Data: محولات MediaStore/SAF في Android وPhotoKit في iOS.
4. Export: حفظ الملفات عبر واجهات اختيار الوجهة الرسمية.
5. Privacy: إدارة الموافقات، أقل صلاحية، سجلات منقحة.

## نموذج النتيجة
- id: معرف داخلي مؤقت.
- mediaType: image | video.
- displayName: اسم العرض عند توفره.
- source: media_library | user_selected_folder | backup_guidance.
- recoveryStatus: accessible | trash_supported | backup_only | unavailable.
- explanation: نص يشرح سبب الحالة.
- localUri: مرجع محلي لا يُرسل إلى أي خادم.

لا يُخزّن محتوى الوسائط في قاعدة بيانات دائمة في MVP. تستخدم الذاكرة المؤقتة أثناء الجلسة، وتُمسح عند الإغلاق أو بطلب المستخدم.

## صلاحيات Android
- طلب صلاحيات قراءة الوسائط الملائمة لإصدار النظام فقط، وبسياق واضح.
- التعامل مع صلاحيات الصور/الفيديو الجزئية حيث يدعمها النظام.
- دعم اختيار مجلد/ملفات بواسطة Storage Access Framework.
- عدم استخدام صلاحية الوصول الشامل للتخزين كخيار افتراضي.
- لا Root ولا مسح منخفض المستوى.

## صلاحيات iOS
- PhotoKit authorization مع مستوى الوصول الذي يختاره المستخدم.
- دعم limited library access.
- عدم افتراض إمكانية الوصول إلى Recently Deleted.
- استخدام document picker لأي ملفات يختارها المستخدم بنفسه.

## تدفق البيانات
User action → Permission rationale → OS authorization → Platform media adapter → Domain classifier → Local results UI → User-selected export destination.

كل طبقة منصة تعيد بيانات وصفية لازمة فقط. لا توجد شبكة في مسار الفحص أو الاستعادة ضمن MVP.

## الاختبارات
- Unit: تصنيف recoveryStatus، معالجة الإلغاء، فرز النتائج.
- Android instrumentation: صلاحيات كاملة/محدودة/مرفوضة، SAF، MediaStore، إصدارات API المستهدفة.
- iOS UI tests: limited/full/denied PhotoKit authorization، اختيار ملفات، التصدير.
- Privacy tests: عدم إنشاء طلبات شبكة، عدم تسجيل أسماء/مسارات الوسائط.
- Accessibility/RTL: TalkBack/VoiceOver، تكبير النص، اتجاه النص والأيقونات.

## بوابة البناء
لا توصف النسخة بأنها قابلة للتثبيت قبل وجود مشروع Gradle/Xcode مكتمل ونجاح build موثق. ولا توصف بأنها جاهزة للمتجر قبل مراجعة سياسات المتجر والخصوصية واختبار الأجهزة.