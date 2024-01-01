document.getElementById('fetchQuestion').addEventListener('click', function () {
    fetch('/get-question')
        .then(response => response.json())
        .then(data => {
            document.getElementById('question').innerText = data.questionText;
            document.getElementById('question').setAttribute('data-id', data.questionId);
            document.getElementById('answer').value = ''; // Clear previous answer
            document.getElementById('result').innerHTML = ''; // Clear previous results
        })
        .catch(error => console.error('Error:', error));
});

document.getElementById('submitAnswer').addEventListener('click', function () {
    const questionId = document.getElementById('question').getAttribute('data-id');
    const userAnswer = document.getElementById('answer').value;

    fetch('/grade', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ questionId, userAnswer }),
    })
        .then(response => response.json())
        .then(data => {
            let totalScore = 0;
            let maxTotalScore = 0;
            const results = data.map(score => {
                totalScore += score.score;
                maxTotalScore += score.maxScore;
                const percentage = (score.score / score.maxScore) * 100;
                const scoreClass = percentage < 50 ? 'zero-score' : (percentage < 75 ? 'partial-score' : 'max-score');
                const feedbackHtml = score.feedback ? `<div class='feedback'>Feedback: ${score.feedback}</div>` : '';

                return `<div class='score-category ${scoreClass}'>
                        <strong>${score.category}</strong>: ${score.score}/${score.maxScore}
                        ${feedbackHtml}
                    </div>`;
            }).join('');

            const totalPercentage = (totalScore / maxTotalScore) * 100;
            const totalResultClass = totalPercentage < 50 ? 'zero-score' : (totalPercentage < 75 ? 'partial-score' : 'max-score');
            const totalResultsHtml = `<div class='total-results ${totalResultClass}'>
                                      Total Marks: ${totalScore}/${maxTotalScore}
                                  </div>`;

            document.getElementById('result').innerHTML = `${totalResultsHtml}Grading Breakdown:<br>${results}`;
        })
        .catch(error => console.error('Error:', error));
});
