Generate videos with Veo 3.1 in Gemini API

Veo 3.1 is Google's state-of-the-art model for generating high-fidelity, 8-second 720p, 1080p or 4k videos featuring stunning realism and natively generated audio. You can access this model programmatically using the Gemini API. To learn more about the available Veo model variants, see the Model Versions section.

Veo 3.1 excels at a wide range of visual and cinematic styles and introduces several new capabilities:

Portrait videos: Choose between landscape (16:9) and portrait (9:16) videos.
Video extension: Extend videos that were previously generated using Veo.
Frame-specific generation: Generate a video by specifying the first and/or last frames.
Image-based direction: Use up to three reference images to guide the content of your generated video.
For more information about writing effective text prompts for video generation, see the Veo prompt guide

Text to video generation
Choose an example to see how to generate a video with dialogue, cinematic realism, or creative animation:

Dialogue & Sound Effects Cinematic Realism Creative Animation


Control the aspect ratio
Veo 3.1 lets you create landscape (16:9, the default setting) or portrait (9:16) videos. You can tell the model which one you want using the aspect_ratio parameter:


Control the resolution
Veo 3.1 can also directly generate 720p, 1080p or 4k videos.

Note that the higher the resolution, the higher the latency will be. 4k videos are also more pricey (cf. pricing).

Video extension is also limited to 720p videos.


Image to video generation
The following code demonstrates generating an image using Gemini 2.5 Flash Image aka Nano Banana, then using that image as the starting frame for generating a video with Veo 3.1.

Using reference images
Note: This feature is available for Veo 3.1 models only.
Veo 3.1 now accepts up to 3 reference images to guide your generated video's content. Provide images of a person, character, or product to preserve the subject's appearance in the output video.

For example, using these three images generated with Nano Banana as references with a well-written prompt creates the following video:

`dress_image`	`woman_image`	`glasses_image`
High-fashion flamingo dress with layers of pink and fuchsia feathers	Beautiful woman with dark hair and warm brown eyes	Whimsical pink, heart-shaped sunglasses

Using first and last frames
Note: This feature is available for Veo 3.1 models only
Veo 3.1 lets you create videos using interpolation, or specifying the first and last frames of the video. For information about writing effective text prompts for video generation, see the Veo prompt guide.

`first_image`	`last_image`	veo3.1_with_interpolation.mp4
A ghostly woman with long white hair and a flowing dress swings gently on a rope swing	The ghostly woman vanishes from the swing	A cinematic, haunting video of an eerie woman disappearing from a swing in the mist
Extending Veo videos
Note: This feature is available for Veo 3.1 models only
Use Veo 3.1 to extend videos that you previously generated with Veo by 7 seconds and up to 20 times.

Input video limitations:

Veo-generated videos only up to 141 seconds long.
Gemini API only supports video extensions for Veo-generated videos.
The video should come from a previous generation, like operation.response.generated_videos[0].video
Videos are stored for 2 days, but if a video is referenced for extension, its 2-day storage timer resets. You can only extend videos that were generated or referenced in the last two days.
Input videos are expected to have a certain length, aspect ratio, and dimensions:
Aspect ratio: 9:16 or 16:9
Resolution: 720p
Video length: 141 seconds or less
The output of the extension is a single video combining the user input video and the generated extended video for up to 148 seconds of video.

This example takes the a Veo-generated video, shown here with its original prompt, and extends it using the video parameter and a new prompt:

Prompt	Output: butterfly_video
An origami butterfly flaps its wings and flies out of the french doors into the garden.	Origami butterfly flaps its wings and flies out of the french doors into the garden.

For information about writing effective text prompts for video generation, see the Veo prompt guide.

Handling asynchronous operations
Video generation is a computationally intensive task. When you send a request to the API, it starts a long-running job and immediately returns an operation object. You must then poll until the video is ready, which is indicated by the done status being true.

The core of this process is a polling loop, which periodically checks the job's status.

Veo API parameters and specifications
These are the parameters you can set in your API request to control the video generation process.

Parameter	Description	Veo 3.1 & Veo 3.1 Fast	Veo 3 & Veo 3 Fast	Veo 2
prompt	The text description for the video. Supports audio cues.	string	string	string
negativePrompt	Text describing what not to include in the video.	string	string	string
image	An initial image to animate.	Image object	Image object	Image object
lastFrame	The final image for an interpolation video to transition. Must be used in combination with the image parameter.	Image object	Image object	Image object
referenceImages	Up to three images to be used as style and content references.	VideoGenerationReferenceImage object (Veo 3.1 only)	n/a	n/a
video	Video to be used for video extension.	Video object from a previous generation	n/a	n/a
aspectRatio	The video's aspect ratio.	"16:9" (default),
"9:16"

"16:9" (default),
"9:16"	"16:9" (default),
"9:16"
resolution	The video's aspect ratio.	"720p" (default),
"1080p" (only supports 8s duration),
"4k" (only supports 8s duration)

"720p" only for extension	"720p" (default),
"1080p" (only supports 8s duration),
"4k" (only supports 8s duration)

"720p" only for extension	Unsupported
durationSeconds	Length of the generated video.	"4", "6", "8".

Must be "8" when using extension, reference images or with 1080p and 4k resolutions	"4", "6", "8".

Must be "8" when using extension, reference images or with 1080p and 4k resolutions	"5", "6", "8"
personGeneration	Controls the generation of people.
(See Limitations for region restrictions)	Text-to-video & Extension:
"allow_all" only
Image-to-video, Interpolation, & Reference images:
"allow_adult" only	Text-to-video:
"allow_all" only
Image-to-video:
"allow_adult" only	Text-to-video:
"allow_all", "allow_adult", "dont_allow"
Image-to-video:
"allow_adult", and "dont_allow"
Note that the seed parameter is also available for Veo 3 models. It doesn't guarantee determinism, but slightly improves it.

You can customize your video generation by setting parameters in your request. For example you can specify negativePrompt to guide the model.

Veo prompt guide
This section contains examples of videos you can create using Veo, and shows you how to modify prompts to produce distinct results.

Safety filters
Veo applies safety filters across Gemini to help ensure that generated videos and uploaded photos don't contain offensive content. Prompts that violate our terms and guidelines are blocked.

Prompt writing basics
Good prompts are descriptive and clear. To get the most out of Veo, start with identifying your core idea, refine your idea by adding keywords and modifiers, and incorporate video-specific terminology into your prompts.

The following elements should be included in your prompt:

Subject: The object, person, animal, or scenery that you want in your video, such as cityscape, nature, vehicles, or puppies.
Action: What the subject is doing (for example, walking, running, or turning their head).
Style: Specify creative direction using specific film style keywords, such as sci-fi, horror film, film noir, or animated styles like cartoon.
Camera positioning and motion: [Optional] Control the camera's location and movement using terms like aerial view, eye-level, top-down shot, dolly shot, or worms eye.
Composition: [Optional] How the shot is framed, such as wide shot, close-up, single-shot or two-shot.
Focus and lens effects: [Optional] Use terms like shallow focus, deep focus, soft focus, macro lens, and wide-angle lens to achieve specific visual effects.
Ambiance: [Optional] How the color and light contribute to the scene, such as blue tones, night, or warm tones.
More tips for writing prompts
Use descriptive language: Use adjectives and adverbs to paint a clear picture for Veo.
Enhance the facial details: Specify facial details as a focus of the photo like using the word portrait in the prompt.
For more comprehensive prompting strategies, visit Introduction to prompt design.

Prompting for audio
With Veo 3, you can provide cues for sound effects, ambient noise, and dialogue. The model captures the nuance of these cues to generate a synchronized soundtrack.

Dialogue: Use quotes for specific speech. (Example: "This must be the key," he murmured.)
Sound Effects (SFX): Explicitly describe sounds. (Example: tires screeching loudly, engine roaring.)
Ambient Noise: Describe the environment's soundscape. (Example: A faint, eerie hum resonates in the background.)
These videos demonstrate prompting Veo 3's audio generation with increasing levels of detail.

Prompt	Generated output
More detail (Dialogue and ambience)
A wide shot of a misty Pacific Northwest forest. Two exhausted hikers, a man and a woman, push through ferns when the man stops abruptly, staring at a tree. Close-up: Fresh, deep claw marks are gouged into the tree's bark. Man: (Hand on his hunting knife) "That's no ordinary bear." Woman: (Voice tight with fear, scanning the woods) "Then what is it?" A rough bark, snapping twigs, footsteps on the damp earth. A lone bird chirps.	Two people in the woods encounter signs of a bear.
Less detail (Dialogue)
Paper Cut-Out Animation. New Librarian: "Where do you keep the forbidden books?" Old Curator: "We don't. They keep us."	Animated librarians discussing forbidden books
Try out these prompts yourself to hear the audio! Try Veo 3

Prompting with reference images
You can use one or more images as inputs to guide your generated videos, using Veo's image-to-video capabilities. Veo uses the input image as the initial frame. Select an image closest to what you envision as the first scene of your video to animate everyday objects, bring drawings and paintings to life, and add movement and sound to nature scenes.

Prompt	Generated output
Input image (Generated by Nano Banana)
A hyperrealistic macro photo of tiny, miniature surfers riding ocean waves inside a rustic stone bathroom sink. A vintage brass faucet is running, creating the perpetual surf. Surreal, whimsical, bright natural lighting.	Tiny, miniature surfers riding ocean waves inside a rustic stone bathroom sink.
Output Video (Generated by Veo 3.1)
A surreal, cinematic macro video. Tiny surfers ride perpetual, rolling waves inside a stone bathroom sink. A running vintage brass faucet generates the endless surf. The camera slowly pans across the whimsical, sunlit scene as the miniature figures expertly carve the turquoise water.	Tiny surfers circling the waves in a bathroom sink.
Veo 3.1 lets you reference images or ingredients to direct your generated video's content. Provide up to three asset images of a single person, character, or product. Veo preserves the subject's appearance in the output video.

Prompt	Generated output
Reference image (Generated by Nano Banana)
A deep sea angler fish lurks in the deep dark water, teeth bared and bait glowing.	A dark and glowing angler fish
Reference image (Generated by Nano Banana)
A pink child's princess costume complete with a wand and tiara, on a plain product background.	A childs pink princess constume
Output Video (Generated by Veo 3.1)
Create a silly cartoon version of the fish wearing the costume, swimming and waving the wand around.	An angler fish wearing a princess costume
Using Veo 3.1, you can also generate videos by specifying the first and last frames of the video.

Prompt	Generated output
First image (Generated by Nano Banana)
A high quality photorealistic front image of a ginger cat driving a red convertible racing car on the French riviera coast.	A ginger cat driving a red convertible racing car
Last image (Generated by Nano Banana)
Show what happens when the car takes off from a cliff.	A ginger cat driving a red convertible goes off a cliff
Output Video (Generated by Veo 3.1)
Optional	A cat drives of a cliff and takes off
This feature gives you precise control over your shot's composition by letting you define the starting and ending frame. Upload an image or use a frame from a previous video generation to make sure your scene begins and concludes exactly as you envision it.

Prompting for extension
To extend your Veo-generated video with Veo 3.1, use the video as an input along with an optional text prompt. Extend finalizes the final second or 24 frames of your video and continues the action.

Note that voice is not able to be effectively extended if it's not present in the last 1 second of video.

Prompt	Generated output
Input video (Generated by Veo 3.1)
The paraglider takes off from the top of the mountain and starts gliding down the mountains overlooking the flower covered valleys below.	A paraglider takes off from the top of a mountain
Output Video (Generated by Veo 3.1)
Extend this video with the paraglider slowly descending.	A paraglider takes off from the top of a mountain, then slowly descends
Example prompts and output
This section presents several prompts, highlighting how descriptive details can elevate the outcome of each video.

Icicles
This video demonstrates how you can use the elements of prompt writing basics in your prompt.

Prompt	Generated output
Close up shot (composition) of melting icicles (subject) on a frozen rock wall (context) with cool blue tones (ambiance), zoomed in (camera motion) maintaining close-up detail of water drips (action).	Dripping icicles with a blue background.
Man on the phone
These videos demonstrate how you can revise your prompt with increasingly specific details to get Veo to refine the output to your liking.

Prompt	Generated output
Less detail
The camera dollies to show a close up of a desperate man in a green trench coat. He's making a call on a rotary-style wall phone with a green neon light. It looks like a movie scene.	Man talking on the phone.
More detail
A close-up cinematic shot follows a desperate man in a weathered green trench coat as he dials a rotary phone mounted on a gritty brick wall, bathed in the eerie glow of a green neon sign. The camera dollies in, revealing the tension in his jaw and the desperation etched on his face as he struggles to make the call. The shallow depth of field focuses on his furrowed brow and the black rotary phone, blurring the background into a sea of neon colors and indistinct shadows, creating a sense of urgency and isolation.	Man talking on the phone
Snow leopard
Prompt	Generated output
Simple prompt:
A cute creature with snow leopard-like fur is walking in winter forest, 3D cartoon style render.	Snow leopard is lethargic.
Detailed prompt:
Create a short 3D animated scene in a joyful cartoon style. A cute creature with snow leopard-like fur, large expressive eyes, and a friendly, rounded form happily prances through a whimsical winter forest. The scene should feature rounded, snow-covered trees, gentle falling snowflakes, and warm sunlight filtering through the branches. The creature's bouncy movements and wide smile should convey pure delight. Aim for an upbeat, heartwarming tone with bright, cheerful colors and playful animation.	Snow leopard is running faster.
Examples by writing elements
These examples show you how to refine your prompts by each basic element.

Subject and context
Specify the main focus (subject) and the background or environment (context).

Prompt	Generated output
An architectural rendering of a white concrete apartment building with flowing organic shapes, seamlessly blending with lush greenery and futuristic elements	Placeholder.
A satellite floating through outer space with the moon and some stars in the background.	Satellite floating in the atmosphere.
Action
Specify what the subject is doing (e.g., walking, running, or turning their head).

Prompt	Generated output
A wide shot of a woman walking along the beach, looking content and relaxed towards the horizon at sunset.	Sunset is absolutely beautiful.
Style
Add keywords to steer the generation toward a specific aesthetic (e.g., surreal, vintage, futuristic, film noir).

Prompt	Generated output
Film noir style, man and woman walk on the street, mystery, cinematic, black and white.	Film noir style is absolutely beautiful.
Camera motion and composition
Specify how the camera moves (POV shot, aerial view, tracking drone view) and how the shot is framed (wide shot, close-up, low angle).

Prompt	Generated output
A POV shot from a vintage car driving in the rain, Canada at night, cinematic.	Sunset is absolutely beautiful.
Extreme close-up of a an eye with city reflected in it.	Sunset is absolutely beautiful.
Ambiance
Color palettes and lighting influence the mood. Try terms like "muted orange warm tones," "natural light," "sunrise," or "cool blue tones."

Prompt	Generated output
A close-up of a girl holding adorable golden retriever puppy in the park, sunlight.	A puppy in a young girl's arms.
Cinematic close-up shot of a sad woman riding a bus in the rain, cool blue tones, sad mood.	A woman riding on a bus that feels sad.
Negative prompts
Negative prompts specify elements you don't want in the video.

❌ Don't use instructive language like no or don't. (e.g., "No walls").
✅ Do describe what you don't want to see. (e.g., "wall, frame").
Prompt	Generated output
Without Negative Prompt:
Generate a short, stylized animation of a large, solitary oak tree with leaves blowing vigorously in a strong wind... [truncated]	Tree with using words.
With Negative Prompt:
[Same prompt]

Negative prompt: urban background, man-made structures, dark, stormy, or threatening atmosphere.	Tree with no negative words.
Aspect ratios
Veo lets you specify the aspect ratio for your video.

Prompt	Generated output
Widescreen (16:9)
Create a video with a tracking drone view of a man driving a red convertible car in Palm Springs, 1970s, warm sunlight, long shadows.	A man driving a red convertible car in Palm Springs, 1970s style.
Portrait (9:16)
Create a video highlighting the smooth motion of a majestic Hawaiian waterfall within a lush rainforest. Focus on realistic water flow, detailed foliage, and natural lighting to convey tranquility. Capture the rushing water, misty atmosphere, and dappled sunlight filtering through the dense canopy. Use smooth, cinematic camera movements to showcase the waterfall and its surroundings. Aim for a peaceful, realistic tone, transporting the viewer to the serene beauty of the Hawaiian rainforest.	A majestic Hawaiian waterfall in a lush rainforest.
Limitations
Request latency: Min: 11 seconds; Max: 6 minutes (during peak hours).
Regional limitations: In EU, UK, CH, MENA locations, the following are the allowed values for personGeneration:
Veo 3: allow_adult only.
Veo 2: dont_allow and allow_adult. Default is dont_allow.
Video retention: Generated videos are stored on the server for 2 days, after which they are removed. To save a local copy, you must download your video within 2 days of generation. Extended videos are treated as newly generated videos.
Watermarking: Videos created by Veo are watermarked using SynthID, our tool for watermarking and identifying AI-generated content. Videos can be verified using the SynthID verification platform.
Safety: Generated videos are passed through safety filters and memorization checking processes that help mitigate privacy, copyright and bias risks.
Audio error: Veo 3.1 will sometimes block a video from generating because of safety filters or other processing issues with the audio. You will not be charged if your video is blocked from generating.
Model features
Feature	Description	Veo 3.1 & Veo 3.1 Fast	Veo 3 & Veo 3 Fast	Veo 2
Audio	Natively generates audio with video.	Natively generates audio with video.	✔️ Always on	❌ Silent only
Input Modalities	The type of input used for generation.	Text-to-Video, Image-to-Video, Video-to-Video	Text-to-Video, Image-to-Video	Text-to-Video, Image-to-Video
Resolution	The output resolution of the video.	720p, 1080p (8s length only), 4k (8s length only)

720p only when using video extension.	720p & 1080p (16:9 only)	720p
Frame Rate	The output frame rate of the video.	24fps	24fps	24fps
Video Duration	Length of the generated video.	8 seconds, 6 seconds, 4 seconds

8 seconds only if 1080p or 4k or using reference images	8 seconds	5-8 seconds
Videos per Request	Number of videos generated per request.	1	1	1 or 2
Status & Details	Model availability and further details.	Preview	Stable	Stable
Model versions
Check out the Pricing and Rate limits pages for more Veo model-specific usage details.

Veo Fast versions allow developers to create videos with sound while maintaining high quality and optimizing for speed and business use cases. They're ideal for backend services that programmatically generate ads, tools for rapid A/B testing of creative concepts, or apps that need to quickly produce social media content.