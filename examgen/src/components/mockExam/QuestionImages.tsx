import type { ExamImage } from '../../types';

function QuestionImages({ images }: { images?: ExamImage[] }) {
  const visibleImages = Array.isArray(images) ? images.filter(isVisibleQuestionImage) : [];
  if (visibleImages.length === 0) {
    return null;
  }

  return (
    <div className="question-images">
      {visibleImages.map((image) => (
        <figure key={image.id || image.src}>
          <img src={image.src} alt={image.alt || `Image from page ${image.page_number || ''}`} />
          {image.page_number && <figcaption>Page {image.page_number}</figcaption>}
        </figure>
      ))}
    </div>
  );
}

function isVisibleQuestionImage(image: ExamImage): boolean {
  if (!image?.src) {
    return false;
  }
  const width = Number(image.width || 0);
  const height = Number(image.height || 0);
  return width >= 80 && height >= 80;
}

export default QuestionImages;

